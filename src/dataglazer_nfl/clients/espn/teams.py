"""Team directory, rosters and depth charts."""

from __future__ import annotations

import re
from typing import Any

from .http import _core_get, _get

# Rosters are small but there are 32 of them, and this API is undocumented with
# no published rate limit, so the league-wide pull goes out a few at a time
# rather than all at once.
_ROSTER_MAX_WORKERS = 4


def get_teams() -> list[dict[str, Any]]:
    """All 32 teams as {id, abbreviation, name, location, display_name}.

    ESPN numbers its teams its own way — Kansas City is 12, and 1 is Atlanta —
    and those IDs match no other NFL data source, so anything addressing this
    API has to resolve names through here rather than reusing an ID from
    elsewhere.

    Raw payload (~145 KB), openable in a browser:
        https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams

    Teams are buried at `sports[0].leagues[0].teams[]`, each under a `team` key
    holding colors, logos, links and record.
    """
    data = _get("teams")
    league = (data.get("sports") or [{}])[0].get("leagues") or [{}]
    teams = []
    for entry in league[0].get("teams", []):
        team = entry.get("team") or {}
        if team.get("id") is None:
            continue
        teams.append(
            {
                "id": str(team["id"]),
                "abbreviation": team.get("abbreviation", ""),
                "name": team.get("name", ""),
                "location": team.get("location", ""),
                "display_name": team.get("displayName", ""),
            }
        )
    return teams


def resolve_team_id(team: str | int) -> str:
    """Return an ESPN team ID from a numeric value or a team name."""
    text = str(team).strip()
    if text.isdigit():
        return text
    want = text.lower()
    teams = get_teams()
    # Abbreviations are matched exactly and first, so "NE" resolves to New
    # England instead of hitting "New Orleans" on the substring pass below.
    for entry in teams:
        if entry["abbreviation"].lower() == want:
            return entry["id"]
    for entry in teams:
        if want in entry["display_name"].lower():
            return entry["id"]
    raise ValueError(f"No ESPN team found matching {team!r}")


# Depth chart entries name their player by URL —
# ".../seasons/2025/athletes/3139477?lang=en&region=us" — and the ID in that
# path is the same one the roster payload uses, so the two join locally. Note
# this is ESPN's athlete ID, which like its team IDs is ESPN's own numbering and
# will not match IDs carried by any other NFL data source.
_ATHLETE_REF = re.compile(r"/athletes/(\d+)")


def get_depth_chart(team_id: str | int, season: int) -> dict[str, list[dict[str, Any]]]:
    """Depth chart for one team as {athlete_id: [{unit, position, rank, slot}]}.

    A player can hold more than one spot — a punter is usually also the holder,
    and a guard is often listed at both LG and RG — so each ID maps to a list,
    sorted best rank first.

    `rank` is per position, not per team: rank 1 at RCB and rank 1 at QB are
    both starters at their own spot. Where a formation starts several players
    at one position the starters are the first N ranks, so a "3WR 1TE" set
    starts WR ranks 1, 2 and 3 — meaning "rank == 1" alone under-counts the
    offense by two receivers.

    `season` is required by the URL but does not select a historical chart:
    2021, 2025 and 2026 all return today's chart, identical apart from the year
    echoed back inside the athlete refs. There is no way to ask this endpoint
    what a depth chart looked like in the past.

    Raw payload (~25 KB), openable in a browser — note this is the *core* host,
    not the site host the other calls use:
        https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/seasons/2025/teams/12/depthcharts

    Team 12 is Kansas City. Units are in `items[]`; players appear as `$ref`
    URLs rather than inline objects, which is why athlete IDs are regexed out
    of them instead of read from a field.
    """
    team_id = resolve_team_id(team_id)
    data = _core_get(f"seasons/{season}/teams/{team_id}/depthcharts")

    by_athlete: dict[str, list[dict[str, Any]]] = {}
    for unit in data.get("items") or []:
        # ESPN's own formation label — "3WR 1TE", "Base 4-3 D", "Special Teams".
        # Kept verbatim rather than bucketed into offense/defense, since the
        # names vary by team and the scheme is part of the answer.
        unit_name = unit.get("name") or ""
        for slot in (unit.get("positions") or {}).values():
            position = (slot.get("position") or {}).get("abbreviation") or ""
            for entry in slot.get("athletes") or []:
                ref = (entry.get("athlete") or {}).get("$ref") or ""
                match = _ATHLETE_REF.search(ref)
                if not match:
                    continue
                by_athlete.setdefault(match.group(1), []).append(
                    {
                        "unit": unit_name,
                        "position": position,
                        "rank": entry.get("rank"),
                        "slot": entry.get("slot"),
                    }
                )

    for entries in by_athlete.values():
        entries.sort(key=lambda e: (e["rank"] is None, e["rank"]))
    return by_athlete


def get_team_roster(team_id: str | int, season: int | None = None) -> dict[str, Any]:
    """Raw team payload with the roster attached — one request, not cached.

    Injury records change daily, so unlike a finished game's summary there is
    nothing here worth storing.

    Passing `season` folds in the team's depth chart, at the cost of a second
    request. Every athlete then carries `rank` (its best depth-chart rank, so a
    starter is 1) and `depth` (every spot it holds, best rank first). Players
    with no depth-chart entry — most of a 90-man roster — get rank None rather
    than being dropped, so the roster stays complete either way.

    Raw payload (~404 KB), openable in a browser:
        https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/12?enable=roster,projection,stats

    Team 12 is Kansas City. Players are at `team.athletes[]`, each carrying its
    `injuries[]` inline — that is what `get_team_injuries` reads. The `enable`
    parameter is what attaches the roster; without it you get the team stub
    only. `team` also holds record, franchise, logos and nextEvent.
    """
    payload = _get(f"teams/{team_id}", enable="roster,projection,stats")
    if season is None:
        return payload

    depth = get_depth_chart(team_id, season)
    for athlete in (payload.get("team") or {}).get("athletes") or []:
        entries = depth.get(str(athlete.get("id"))) or []
        athlete["rank"] = entries[0]["rank"] if entries else None
        athlete["depth"] = entries
    return payload
