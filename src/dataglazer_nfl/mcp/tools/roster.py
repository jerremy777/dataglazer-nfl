"""Roster tools — live rather than a week rollup, so uncached."""

from __future__ import annotations

from typing import Any

from dataglazer_nfl.clients import espn

from ..app import mcp


@mcp.tool()
def list_roster(
    team: str | int | None = None,
    position: str | None = None,
    include_depth: bool = True,
) -> list[dict[str, Any]]:
    """Full NFL roster with player biography — height, weight, age, draft, contract.

    One row per player for one team or the whole league. This is the tool for
    questions about who a player *is* rather than what he did in a given week:
    how tall a starting offensive line is, what a safety weighs, how old a
    position group is, what a first-rounder is being paid. The weekly tools
    cover production; nothing else here covers biography.

    A numeric `team` is an ESPN team ID (Kansas City is 12), which is worth
    stating because ESPN's numbering is its own and matches no other NFL data
    source; passing a name avoids the question entirely. ESPN offers no position
    filter, so `position` is applied client-side after the fetch.

    Three fields repay a second of care:

    - **`status` is roster standing, not health.** It reads "Day-To-Day" even
      for a player on season-ending injured reserve. Use `injury_status` for
      health — it is None for a healthy player and carries ESPN's real label
      ("Out", "Questionable", "Injured Reserve") otherwise.
    - **`draft` and `contract` are None for roughly half a roster.** Undrafted
      free agents are a large minority of a 90-man roster, and ESPN carries no
      contract for many of the rest. Treat their absence as normal, not as a
      failed lookup.
    - **`rank` is per position, not per team**, and a formation can start
      several players at one position — a "3WR 1TE" set starts WR ranks 1, 2 and
      3, so filtering on `rank == 1` under-counts the starting offense. See
      `list_injuries` for the full set of caveats; `depth` lists every spot a
      player holds, so prefer it over `rank` when the unit matters.

    Args:
        team: Team name (e.g. "Chiefs", "KC") or numeric ESPN team ID. If
            omitted, pulls all 32 teams — roughly 2,900 players over 64
            requests (roster plus depth chart per team), issued a few at a time.
        position: Filter to a position code, e.g. "QB", "RB", "WR" (exact,
            case-insensitive). Matches the player's roster position, not the
            depth-chart slot inside `depth`.
        include_depth: Attach `rank` and `depth`. Costs a second request per
            team, so turning it off halves a league-wide pull from 64 requests
            to 32. Off, the two keys are absent rather than null.

    Returns [{name, espn_id, team, position, position_name, jersey, height_in,
    height, weight_lb, age, birth_date, birth_place, experience_years, status,
    rank, depth, headshot, draft, contract, injury_status, injuries}].

    `height_in` and `weight_lb` are integers (71, 180); `height` is the display
    form ("5' 11\""). `headshot` is a PNG URL, None for the newest rookies —
    ESPN has no photo for roughly one player in ten. `draft` is
    {year, round, pick, text} with `pick` the overall selection number, and
    `contract` is {salary, bonus, salary_remaining, years_remaining,
    signed_through} in whole dollars — both None where ESPN has nothing.
    `injuries` is a list of {status, type, location, detail, side, return_date,
    date, comment}, where `type` is the body part ("Knee"), `location` the
    region ("Leg"), `detail` the nature ("Soreness") and `side` which one; it is
    empty for a healthy player. `rank` and `depth` are omitted entirely when
    `include_depth` is false.

    Note ESPN returns no college on this endpoint — the field is empty for every
    player on all 32 teams, so it is not returned here.
    """
    if team is not None:
        rows = espn.get_team_players(espn.resolve_team_id(team), include_depth=include_depth)
    else:
        rows = espn.get_league_players(include_depth=include_depth)

    if position:
        want = position.strip().lower()
        rows = [r for r in rows if (r.get("position") or "").lower() == want]

    return rows
