"""Single-week rollups — the four recurring dataglazer series."""

from __future__ import annotations

from typing import Any

from dataglazer_nfl.clients import espn
from dataglazer_nfl.config import CURRENT_SEASON

from ..app import mcp


@mcp.tool()
def list_week_games(
    week: int,
    year: int = CURRENT_SEASON,
    season_type: int = 2,
) -> list[dict[str, Any]]:
    """List a week's NFL games and whether each one has finished.

    Useful as a cheap pre-check before pulling a week's stats: the weekly stat
    tools only aggregate completed games, so a week that is still in progress
    will report partial numbers.

    Args:
        week: Week number within the season type (1-18 for the regular season).
        year: Season year (YYYY), e.g. 2025 for the 2025-26 season.
        season_type: 1 = preseason, 2 = regular season, 3 = postseason.

    Returns a list of {id, name, status, completed, date} dicts.
    """
    return espn.get_week_events(week, year, season_type)


@mcp.tool()
def get_week_efficiency_leaders(
    week: int,
    year: int = CURRENT_SEASON,
    season_type: int = 2,
    min_attempts: int = 10,
    top_n: int = 10,
) -> list[dict[str, Any]]:
    """Passer rating leaders for ONE week (not season-to-date).

    Backs the "Efficiency Leaders" series. Uses ESPN's own passer rating where
    available and computes the standard formula otherwise.

    Args:
        week: Week number within the season type.
        year: Season year (YYYY).
        season_type: 1 = preseason, 2 = regular season, 3 = postseason.
        min_attempts: Drop passers below this many attempts (filters out
            trick-play and backup throws that produce meaningless ratings).
        top_n: Number of leaders to return.

    Returns [{name, team, rating, comp, att, yards, td, int}] sorted by rating.
    """
    return espn.get_efficiency_leaders(
        week, year, season_type, min_attempts=min_attempts, top_n=top_n
    )


@mcp.tool()
def get_week_workhorse_leaders(
    week: int,
    year: int = CURRENT_SEASON,
    season_type: int = 2,
    min_carries: int = 1,
    top_n: int = 10,
) -> list[dict[str, Any]]:
    """Rushing volume leaders for ONE week (not season-to-date).

    Backs the "Workhorse Watch" series. Ranked by carries, then yards — this is
    a usage board, so the leader is the most-fed back rather than the most
    productive one.

    Args:
        week: Week number within the season type.
        year: Season year (YYYY).
        season_type: 1 = preseason, 2 = regular season, 3 = postseason.
        min_carries: Drop players below this many carries.
        top_n: Number of leaders to return.

    Returns [{name, team, carries, yards, td, long}] sorted by carries.
    """
    return espn.get_workhorse_leaders(
        week, year, season_type, min_carries=min_carries, top_n=top_n
    )


@mcp.tool()
def get_week_big_plays(
    week: int,
    year: int = CURRENT_SEASON,
    season_type: int = 2,
    top_n: int = 5,
    min_yards: int = 20,
    include_returns: bool = False,
) -> dict[str, Any]:
    """The longest plays of ONE week, with geometry for a field map.

    Backs the "Big Play Board" series. Considers plays from scrimmage (runs and
    receptions) by default; kicks and punts are excluded because ESPN reports a
    kick's distance in the same yardage field, which would otherwise fill the
    board with field goals.

    Every play carries a `segments` path that can be drawn directly on a single
    0-100 field, with no need to parse `text`.

    **The frame is the team that put the ball in play** (`frame:
    "snapping_team"`). They attack toward 100; 0 is the goal line they defend.
    On a kickoff the kicking team takes that role, so kick and punt returns
    behave like every other return. Direction therefore carries meaning:
    explosive offensive plays run left to right, while interception, fumble,
    punt and kick returns run right to left with a negative `net`. A pick-six
    draws as a short forward stub hinged into a long backward sweep, and reads
    as a pick-six before any colour or label. The underlying rule is
    "possession changed", not "the defense did it" — a sack would also point
    left — which is safe only while the board stays explosives-only.

    Three yardage numbers, all worth having separately:

    - `yardage` is ESPN's credited stat and what the board sorts on.
    - `path_yards` is the ground the ball actually covered. On an 83-yard punt
      return it is 135, because the punt itself travelled 52 — this is what
      stops a chart labelling an arrow "83" while drawing it 135 long.
    - `net` is signed displacement from the first segment's start to the last
      segment's end, and is what drives arrow direction.

    Args:
        week: Week number within the season type.
        year: Season year (YYYY).
        season_type: 1 = preseason, 2 = regular season, 3 = postseason.
        top_n: Number of plays to return.
        min_yards: Ignore plays shorter than this.
        include_returns: Also consider interception/fumble/punt/kick returns,
            credited to the returning (defensive) team.

    Returns {plays, derived_count}. Each play is {event_id, yardage, text, team,
    type, touchdown, quarter, clock, game_name, opponent, player, unit,
    team_colors, frame, segments, path_yards, net}, sorted by yardage.

    A segment is {from, to, kind, by, origin_source}: `from`/`to` are yard lines
    in the snapping team's frame, `kind` is one of pass / run / punt / kick /
    return / lateral / sack, and `by` is the team that moved the ball on that
    leg — not always the snapping team, since a pick-six's return leg belongs to
    the defense. A play from scrimmage has exactly one segment; anything where
    the ball changed hands has two, so the hinge can be drawn.

    `origin_source` is "play_text" when the yard line was stated in the play
    description and "derived" when it was back-solved, which ESPN forces on
    plays collapsed into a scoring-summary row ("Jacob Cowing 83 Yd Punt
    Return"). `derived_count` says how many of the returned plays contain a
    derived segment, so a chart can dash or footnote them rather than silently
    drawing an inference as a measurement.
    """
    return espn.get_big_play_board(
        week,
        year,
        season_type,
        top_n=top_n,
        min_yards=min_yards,
        include_returns=include_returns,
    )


@mcp.tool()
def get_week_turnover_tracker(
    week: int,
    year: int = CURRENT_SEASON,
    season_type: int = 2,
) -> list[dict[str, Any]]:
    """Team takeaway/giveaway differential for ONE week.

    Backs the "Turnover Tracker" series. Each team's takeaways are read off its
    opponent's giveaways in the same game, so every game contributes two rows
    and the differentials across the week sum to zero.

    Args:
        week: Week number within the season type.
        year: Season year (YYYY).
        season_type: 1 = preseason, 2 = regular season, 3 = postseason.

    Returns [{team, opponent, giveaways, takeaways, diff}] sorted by diff.
    """
    return espn.get_turnover_tracker(week, year, season_type)
