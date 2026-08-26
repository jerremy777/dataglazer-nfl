"""Single-week rollups: the four recurring dataglazer series.

ESPN has no "week N leaders" endpoint, so each series is aggregated locally
from that week's game summaries.
"""

from __future__ import annotations

from typing import Any

from ._parse import _all_plays, _stat_groups, _team_abbrs, _to_int
from .http import REGULAR_SEASON
from .schedule import get_week_summaries

# ---------------------------------------------------------------------------
# 1. Efficiency Leaders — passer rating for the week
# ---------------------------------------------------------------------------


def nfl_passer_rating(comp: int, att: int, yards: int, td: int, ints: int) -> float:
    """Standard NFL passer rating (used when ESPN omits its own RTG)."""
    if att == 0:
        return 0.0
    a = max(0.0, min((comp / att - 0.3) * 5, 2.375))
    b = max(0.0, min((yards / att - 3) * 0.25, 2.375))
    c = max(0.0, min((td / att) * 20, 2.375))
    d = max(0.0, min(2.375 - (ints / att) * 25, 2.375))
    return round((a + b + c + d) / 6 * 100, 1)


def get_efficiency_leaders(
    week: int,
    year: int,
    season_type: int = REGULAR_SEASON,
    min_attempts: int = 10,
    top_n: int = 10,
    summaries: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Passer rating leaderboard for a single week."""
    if summaries is None:
        summaries = get_week_summaries(week, year, season_type)
    results = []

    for game in summaries:
        for abbr, labels, athletes in _stat_groups(game, "passing"):
            for entry in athletes:
                stats = dict(zip(labels, entry.get("stats", [])))
                comp_att = str(stats.get("C/ATT", "0/0"))
                if "/" not in comp_att:
                    continue
                comp, att = (_to_int(x) for x in comp_att.split("/", 1))
                if att < min_attempts:
                    continue
                yards = _to_int(stats.get("YDS"))
                td = _to_int(stats.get("TD"))
                ints = _to_int(stats.get("INT"))
                try:  # ESPN reports its own rating; fall back to computing it
                    rating = round(float(stats["RTG"]), 1)
                except (KeyError, TypeError, ValueError):
                    rating = nfl_passer_rating(comp, att, yards, td, ints)
                results.append(
                    {
                        "name": entry.get("athlete", {}).get("displayName", "Unknown"),
                        "team": abbr,
                        "rating": rating,
                        "comp": comp,
                        "att": att,
                        "yards": yards,
                        "td": td,
                        "int": ints,
                    }
                )

    results.sort(key=lambda r: r["rating"], reverse=True)
    return results[:top_n]


# ---------------------------------------------------------------------------
# 2. Workhorse Watch — carries + yards, single week
# ---------------------------------------------------------------------------


def get_workhorse_leaders(
    week: int,
    year: int,
    season_type: int = REGULAR_SEASON,
    min_carries: int = 1,
    top_n: int = 10,
    summaries: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Rushing volume leaderboard for a single week."""
    if summaries is None:
        summaries = get_week_summaries(week, year, season_type)
    results = []

    for game in summaries:
        for abbr, labels, athletes in _stat_groups(game, "rushing"):
            for entry in athletes:
                stats = dict(zip(labels, entry.get("stats", [])))
                carries = _to_int(stats.get("CAR"))
                if carries < min_carries:
                    continue
                results.append(
                    {
                        "name": entry.get("athlete", {}).get("displayName", "Unknown"),
                        "team": abbr,
                        "carries": carries,
                        "yards": _to_int(stats.get("YDS")),
                        "td": _to_int(stats.get("TD")),
                        "long": _to_int(stats.get("LONG")),
                    }
                )

    results.sort(key=lambda r: (r["carries"], r["yards"]), reverse=True)
    return results[:top_n]


# ---------------------------------------------------------------------------
# 3. Big Play Board — longest plays of the week
# ---------------------------------------------------------------------------

# statYardage is populated for every play type, including kicks — a field goal
# reports its kick distance and a kickoff its kick/return distance. Ranking raw
# statYardage therefore returns a board of punts and FGs, so restrict to plays
# that represent an actual gain.
SCRIMMAGE_PLAY_TYPES = {
    "Rush",
    "Rushing Touchdown",
    "Pass Reception",
    "Passing Touchdown",
}

RETURN_PLAY_TYPES = {
    "Pass Interception Return",
    "Interception Return Touchdown",
    "Fumble Return Touchdown",
    "Punt Return Touchdown",
    "Kickoff Return Touchdown",
}


def get_big_play_board(
    week: int,
    year: int,
    season_type: int = REGULAR_SEASON,
    top_n: int = 5,
    min_yards: int = 20,
    include_returns: bool = False,
    summaries: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """The week's longest plays.

    Defaults to plays from scrimmage (runs and receptions). Set
    `include_returns=True` to also consider interception/punt/kick returns,
    which are credited to the returning (defensive) team.
    """
    if summaries is None:
        summaries = get_week_summaries(week, year, season_type)

    wanted = SCRIMMAGE_PLAY_TYPES | (RETURN_PLAY_TYPES if include_returns else set())
    results = []

    for game in summaries:
        abbrs = _team_abbrs(game)
        for play in _all_plays(game):
            play_type = (play.get("type") or {}).get("text", "")
            if play_type not in wanted:
                continue
            yardage = play.get("statYardage")
            if yardage is None or yardage < min_yards:
                continue

            # On a return the yards belong to the defense; otherwise the offense.
            side = "defense" if play_type in RETURN_PLAY_TYPES else "offense"
            team_id = next(
                (
                    str(p.get("id"))
                    for p in play.get("teamParticipants") or []
                    if p.get("type") == side
                ),
                None,
            )
            if team_id is None:  # e.g. two-point attempts omit participant types
                team_id = str((play.get("start", {}).get("team") or {}).get("id", ""))

            results.append(
                {
                    "yardage": yardage,
                    "text": play.get("text", ""),
                    "team": abbrs.get(team_id, ""),
                    "type": play_type,
                    "touchdown": "Touchdown" in play_type,
                    "quarter": (play.get("period") or {}).get("number"),
                }
            )

    results.sort(key=lambda r: r["yardage"], reverse=True)
    return results[:top_n]


# ---------------------------------------------------------------------------
# 4. Turnover Tracker — team takeaway/giveaway differential, single week
# ---------------------------------------------------------------------------


def get_turnover_tracker(
    week: int,
    year: int,
    season_type: int = REGULAR_SEASON,
    summaries: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """One row per team: giveaways, takeaways and differential for the week.

    A team's takeaways are its opponent's giveaways, so both sides are derived
    from the same game rather than looked up across the league.
    """
    if summaries is None:
        summaries = get_week_summaries(week, year, season_type)
    results = []

    for game in summaries:
        team_blocks = game.get("boxscore", {}).get("teams", [])
        if len(team_blocks) != 2:
            continue

        parsed = []
        for block in team_blocks:
            stats = block.get("statistics", [])
            entry = next((s for s in stats if s.get("name") == "turnovers"), None)
            parsed.append(
                (
                    block.get("team", {}).get("abbreviation", ""),
                    _to_int(entry.get("displayValue") if entry else 0),
                )
            )

        (abbr_a, gv_a), (abbr_b, gv_b) = parsed
        results.append(
            {
                "team": abbr_a,
                "opponent": abbr_b,
                "giveaways": gv_a,
                "takeaways": gv_b,
                "diff": gv_b - gv_a,
            }
        )
        results.append(
            {
                "team": abbr_b,
                "opponent": abbr_a,
                "giveaways": gv_b,
                "takeaways": gv_a,
                "diff": gv_a - gv_b,
            }
        )

    results.sort(key=lambda r: r["diff"], reverse=True)
    return results
