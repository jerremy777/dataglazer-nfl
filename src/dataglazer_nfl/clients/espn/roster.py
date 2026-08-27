"""Player biography rows — height, weight, age, draft, contract, injury.

The weekly rollups say what a player did; this says who he is. Everything comes
off the team payload `get_team_roster` already fetches, which
`get_team_injuries` reads only the `injuries[]` array from — height, weight,
age, draft and contract are in hand on every one of those calls and thrown
away. This module is the flattening layer over that same payload.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any

from dataglazer_nfl.config import DEPTH_CHART_SEASON

from .teams import _ROSTER_MAX_WORKERS, get_team_roster, get_teams, resolve_team_id


def _int_or_none(value: Any) -> int | None:
    """ESPN sends height and weight as whole-numbered floats (71.0, 180.0).

    They are measurements, not quantities with a fractional part, and "71.0" in
    a chart label is noise — so they come back as ints.
    """
    return None if value is None else int(value)


def _birth_place(place: dict[str, Any] | None) -> str | None:
    """ "New Orleans, LA, USA" from ESPN's {city, state, country}.

    Any of the three can be missing — international players carry a country and
    no state — so this joins whatever is present rather than assuming a shape.
    """
    parts = [(place or {}).get(key) for key in ("city", "state", "country")]
    return ", ".join(p for p in parts if p) or None


def _draft(athlete: dict[str, Any]) -> dict[str, Any] | None:
    """Draft slot, or None for an undrafted player.

    ESPN omits the `draft` key entirely rather than sending an empty object, so
    roughly half a roster has no key at all — undrafted free agents are a large
    minority of a 90-man roster, not an edge case.
    """
    draft = athlete.get("draft")
    if not draft:
        return None
    return {
        "year": draft.get("year"),
        "round": draft.get("round"),
        # ESPN calls the overall pick number `selection`; renamed because
        # "pick 176" is how anyone reading a chart would say it.
        "pick": draft.get("selection"),
        "text": draft.get("displayText"),
    }


def _contract(athlete: dict[str, Any]) -> dict[str, Any] | None:
    """Current contract terms, or None when ESPN carries none.

    Note the key is singular `contract` on this endpoint. The other roster
    endpoint (`teams/{id}/roster`) has a plural `contracts` holding a
    salary-per-season list instead — a different shape under a near-identical
    name, so this is worth being explicit about.

    Salaries are whole dollars, not thousands or millions.
    """
    contract = athlete.get("contract")
    if not contract:
        return None
    return {
        "salary": contract.get("salary"),
        "bonus": contract.get("bonus"),
        "salary_remaining": contract.get("salaryRemaining"),
        "years_remaining": contract.get("yearsRemaining"),
        "signed_through": contract.get("signedThrough"),
    }


def _injuries(athlete: dict[str, Any]) -> list[dict[str, Any]]:
    """Every injury on record, flattened. Empty for a healthy player.

    ESPN splits an injury across two levels: the status and the beat-reporter
    writeup sit on the entry, while the anatomy lives in `details` — `type` is
    the body part ("Knee"), `location` the region ("Leg"), `detail` the nature
    ("Soreness") and `side` which one ("Left").
    """
    rows = []
    for injury in athlete.get("injuries") or []:
        details = injury.get("details") or {}
        rows.append(
            {
                "status": injury.get("status"),
                "type": details.get("type"),
                "location": details.get("location"),
                "detail": details.get("detail"),
                "side": details.get("side"),
                "return_date": details.get("returnDate"),
                "date": injury.get("date"),
                "comment": injury.get("shortComment"),
            }
        )
    return rows


def _player_row(
    athlete: dict[str, Any],
    abbr: str,
    include_depth: bool = True,
) -> dict[str, Any]:
    """One athlete from the team payload as a flat row.

    Nothing is dropped for missing data — a player with no listed height still
    gets a row, with None in that field — so a roster count is a roster count.
    """
    position = athlete.get("position") or {}
    injuries = _injuries(athlete)

    row: dict[str, Any] = {
        "name": athlete.get("displayName"),
        # ESPN's own athlete numbering, the same one the depth chart keys on.
        # Like its team IDs it matches no other NFL data source.
        "espn_id": athlete.get("id"),
        "team": abbr,
        "position": position.get("abbreviation"),
        "position_name": position.get("displayName"),
        "jersey": athlete.get("jersey"),
        "height_in": _int_or_none(athlete.get("height")),
        # Kept alongside the number because inches -> feet-and-inches is the one
        # conversion a caller would otherwise have to write itself.
        "height": athlete.get("displayHeight"),
        "weight_lb": _int_or_none(athlete.get("weight")),
        "age": athlete.get("age"),
        "birth_date": athlete.get("dateOfBirth"),
        "birth_place": _birth_place(athlete.get("birthPlace")),
        "experience_years": (athlete.get("experience") or {}).get("years"),
        # Roster standing, not health: this reads "Day-To-Day" even for a player
        # on season-ending IR. `injury_status` below is the reliable signal.
        "status": (athlete.get("status") or {}).get("name"),
    }

    if include_depth:
        # Attached by `get_team_roster` when it was passed a season. None/[] for
        # a player on the roster but off the depth chart.
        row["rank"] = athlete.get("rank")
        row["depth"] = athlete.get("depth") or []

    row.update(
        {
            "headshot": (athlete.get("headshot") or {}).get("href"),
            "draft": _draft(athlete),
            "contract": _contract(athlete),
            # Hoisted from the first injury so filtering a roster on "who is
            # Questionable" doesn't mean reaching into a nested list.
            "injury_status": injuries[0]["status"] if injuries else None,
            "injuries": injuries,
        }
    )
    return row


def get_team_players(
    team_id: str | int,
    season: int | None = None,
    include_depth: bool = True,
) -> list[dict[str, Any]]:
    """Full roster for one team, one row per player, ~90-100 rows.

    With `include_depth`, each row carries the player's depth-chart standing,
    which is what separates a starting tackle from the fourth guy at the
    position. That costs one extra request per team; see `get_depth_chart` for
    what `rank` does and does not mean. Turning it off omits `rank` and `depth`
    entirely rather than nulling them, so a `rank` of None keeps its one
    meaning: on the roster, off the depth chart.

    `team_id` may be a name ("Chiefs", "KC") or an ESPN team ID. The name is
    resolved here rather than only in the MCP tool because the depth-chart
    endpoint 404s on anything but a numeric ID, and a notebook calling this
    directly should not have to know that. Resolving a value that is already
    numeric costs nothing.
    """
    team_id = resolve_team_id(team_id)
    team = (
        get_team_roster(
            team_id, season=(season or DEPTH_CHART_SEASON) if include_depth else None
        ).get("team")
        or {}
    )
    abbr = team.get("abbreviation") or team.get("displayName") or str(team_id)
    return [_player_row(a, abbr, include_depth) for a in team.get("athletes") or []]


def get_league_players(
    season: int | None = None,
    include_depth: bool = True,
) -> list[dict[str, Any]]:
    """Every player on all 32 rosters — roughly 2,900 rows.

    Two requests per team — roster and depth chart — so 64 in total, halving to
    32 without `include_depth`. Either way they are issued a few at a time
    against an undocumented API with no published rate limit.
    """
    ids = [entry["id"] for entry in get_teams()]
    if not ids:
        return []
    with ThreadPoolExecutor(max_workers=min(_ROSTER_MAX_WORKERS, len(ids))) as pool:
        per_team = list(pool.map(lambda tid: get_team_players(tid, season, include_depth), ids))
    return [row for team_rows in per_team for row in team_rows]
