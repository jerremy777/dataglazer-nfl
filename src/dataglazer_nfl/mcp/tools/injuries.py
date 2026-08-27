"""Roster tools — live rather than a week rollup, so uncached."""

from __future__ import annotations

from typing import Any

from dataglazer_nfl.clients import espn

from ..app import mcp


@mcp.tool()
def list_injuries(
    team: str | int | None = None,
    status: str | None = None,
    position: str | None = None,
    include_depth: bool = True,
) -> list[dict[str, Any]]:
    """List injured NFL players, with depth-chart standing, for one team or the league.

    Reads ESPN's roster payload, where every player carries their injury record
    inline, and joins the team's depth chart onto it so each row says how much
    the injury costs — a starting left tackle and his third-stringer are the
    same "Questionable" without it. A numeric `team` is an ESPN team ID (Kansas
    City is 12), which is worth stating because ESPN's numbering is its own and
    matches no other NFL data source; passing a name avoids the question
    entirely. ESPN offers no status or position filter, so both are applied
    client-side after the fetch.

    Reading `rank` correctly takes some care:

    - **It is per position, not per team.** Rank 1 at RCB and rank 1 at QB are
      each the starter at their own spot.
    - **A formation can start several players at one position.** In a "3WR 1TE"
      set the starting receivers are WR ranks 1, 2 and 3, so filtering on
      `rank == 1` under-counts the starting offense.
    - **`rank` is the best of several spots when a player holds more than one.**
      A returner buried at WR7 still reports rank 1 off KR1. `depth` lists every
      spot, so use it rather than `rank` when the unit matters.
    - **Rank is today's chart, not the week of the injury.** ESPN serves no
      historical depth charts, and a player who has been out a while may have
      already been moved down or off it.

    Args:
        team: Team name (e.g. "Chiefs", "KC") or numeric ESPN team ID. If
            omitted, pulls all 32 teams — 64 requests (roster plus depth chart
            per team), issued a few at a time.
        status: Filter to an injury status, e.g. "Out", "Questionable",
            "Doubtful", "Injured Reserve" (exact, case-insensitive).
        position: Filter to a position code, e.g. "QB", "RB", "WR" (exact,
            case-insensitive). Matches the player's roster position, not the
            depth-chart slot inside `depth`.
        include_depth: Attach `rank` and `depth`. Costs a second request per
            team, so turning it off halves a league-wide pull from 64 requests
            to 32 — worth it when the question is only who is hurt, not how
            much it matters. Off, the two keys are absent rather than null.

    Returns [{name, team, position, height_in, height, weight_lb, rank, depth,
    status, injury_type, details, date}], where `injury_type` is the body part
    ("Knee", "Foot") and `details` the beat-reporter writeup. `height_in` and
    `weight_lb` are integers (71, 180) and `height` the display form ("5' 11\"") —
    the same keys `list_roster` uses, so rows from the two tools join directly.

    `rank` is the player's best depth-chart rank
    (1 = starter) or None when they are off the chart entirely, and `depth` is
    [{unit, position, rank, slot}] for every spot held, best rank first — `unit`
    being ESPN's formation label ("3WR 1TE", "Base 3-4 D", "Special Teams").
    Both are omitted when `include_depth` is false. Teams with nobody hurt
    simply contribute no rows.
    """
    if team is not None:
        rows = espn.get_team_injuries(espn.resolve_team_id(team), include_depth=include_depth)
    else:
        rows = espn.get_league_injuries(include_depth=include_depth)

    if status:
        want = status.strip().lower()
        rows = [r for r in rows if (r.get("status") or "").lower() == want]

    if position:
        want = position.strip().lower()
        rows = [r for r in rows if (r.get("position") or "").lower() == want]

    return rows
