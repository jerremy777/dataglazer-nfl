"""Injured players, joined onto the depth chart so a starter is distinguishable
from a backup."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any

from dataglazer_nfl.config import DEPTH_CHART_SEASON

from .teams import _ROSTER_MAX_WORKERS, get_team_roster, get_teams


def get_team_injuries(
    team_id: str | int,
    season: int | None = None,
    include_depth: bool = True,
) -> list[dict[str, Any]]:
    """Flattened injury rows for one team, empty when nobody is hurt.

    Every athlete on the roster carries its own `injuries` list inline, so no
    follow-up request per player is needed. Most of them are empty — a healthy
    roster is ~10 injured out of ~95 — and dropping those is the filter.

    With `include_depth`, each row also carries the player's depth-chart
    standing, which is what separates a starter's hamstring from a
    fourth-stringer's. That costs one extra request per team; see
    `get_depth_chart` for what `rank` does and does not mean. Turning it off
    omits the `rank` and `depth` keys entirely rather than nulling them, so a
    `rank` of None keeps its one meaning: on the roster, off the depth chart.
    """
    team = (
        get_team_roster(
            team_id, season=(season or DEPTH_CHART_SEASON) if include_depth else None
        ).get("team")
        or {}
    )
    abbr = team.get("abbreviation") or team.get("displayName") or str(team_id)

    rows = []
    for athlete in team.get("athletes") or []:
        position = athlete.get("position") or {}
        # A list, though ESPN has only ever been observed to carry one entry;
        # looping means a second record shows up rather than being dropped.
        for injury in athlete.get("injuries") or []:
            details = injury.get("details") or {}
            row = {
                "name": athlete.get("displayName"),
                "team": abbr,
                "position": position.get("abbreviation"),
            }
            if include_depth:
                # Best depth-chart rank and every spot held, attached by
                # `get_team_roster`. None/[] for players off the chart.
                row["rank"] = athlete.get("rank")
                row["depth"] = athlete.get("depth") or []
            row.update(
                {
                    "status": injury.get("status"),
                    # ESPN files the body part under `details.type` and the
                    # beat-reporter writeup under `shortComment`; that writeup is
                    # what this returns as `details`.
                    "injury_type": details.get("type"),
                    "details": injury.get("shortComment"),
                    "date": injury.get("date"),
                }
            )
            rows.append(row)
    return rows


def get_league_injuries(
    season: int | None = None,
    include_depth: bool = True,
) -> list[dict[str, Any]]:
    """Flattened injury rows for all 32 teams.

    Two requests per team — roster and depth chart — so 64 in total, halving to
    32 without `include_depth`. Either way they are issued a few at a time
    against an undocumented API with no published rate limit.
    """
    ids = [entry["id"] for entry in get_teams()]
    if not ids:
        return []
    with ThreadPoolExecutor(max_workers=min(_ROSTER_MAX_WORKERS, len(ids))) as pool:
        per_team = list(pool.map(lambda tid: get_team_injuries(tid, season, include_depth), ids))
    return [row for team_rows in per_team for row in team_rows]
