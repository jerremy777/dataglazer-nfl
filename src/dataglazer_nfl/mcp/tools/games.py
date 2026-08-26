"""Single-game tools. Take an `event_id` from `list_week_games`."""

from __future__ import annotations

from typing import Any

from dataglazer_nfl.clients import espn

from ..app import mcp


@mcp.tool()
def get_game_scoring_summary(event_id: str, strict: bool = True) -> dict[str, Any]:
    """Every scoring play in ONE game, tagged offense / defense / special teams.

    Answers "where did these points come from" without reading a recap. Each
    play carries the unit that produced it, so the per-team rollup splits a
    final score into offensive, defensive and special-teams points.

    Two things about the ESPN payload drive how this is computed:

    - **Points come from the running score, not a point table.** ESPN folds the
      try into the touchdown play ("...TOUCHDOWN. T.Loop extra point is GOOD" is
      one play worth 7) and emits no separate extra-point or two-point scoring
      plays. Scoring 6/3/1/2 by play type therefore under-counts every converted
      touchdown; the score delta also absorbs missed extra points (6) and
      two-point tries (8), which is what makes the rollup match the final score.
    - **The scoring team is whichever side's score moved, not the drive's team.**
      A pick-six or punt-return touchdown is filed inside the drive of the team
      that *lost* the ball, so the drive's team is the wrong side on exactly the
      non-offensive scores this tool exists to isolate.

    A try attached to a defensive or special-teams touchdown is counted in that
    category, since ESPN reports it as one play and the unit generated all of it.

    Args:
        event_id: ESPN event ID, as returned by `list_week_games`.
        strict: Raise if a finished game's points don't add up to the official
            final score. Set False to get the numbers with `warnings` instead.

    Returns {event_id, name, completed, scoring_plays, team_totals, team_colors,
    final_score, reconciles, warnings}. Each scoring play is
    {team, quarter, clock, points, category, play_type, description};
    team_totals is {team: {offense_points, defense_points, special_teams_points,
    total_points}}; team_colors is {team: {primary, alternate}} as '#'-prefixed
    hex, ready for matplotlib or CSS.
    """
    return espn.get_game_scoring_summary(event_id, strict=strict)


@mcp.tool()
def get_game_drives(event_id: str) -> dict[str, Any]:
    """Drive-by-drive log for ONE game.

    One row per possession, in order — the natural unit for "which drives led to
    points" charts, and much easier to reason about than raw play-by-play.
    `team` is the team with the ball, so a drive that ended in a pick-six is
    listed under the team that threw it; use `get_game_scoring_summary` for who
    scored.

    Args:
        event_id: ESPN event ID, as returned by `list_week_games`.

    Returns {event_id, name, completed, drives, team_colors}. Each drive is
    {team, quarter_started, description, result, result_detail, yards, plays,
    time_of_possession, is_score}, where `result` is ESPN's short code ("TD",
    "FG", "PUNT", "INT", "DOWNS", "END OF HALF") and `result_detail` its
    spelled-out form. team_colors is {team: {primary, alternate}} as
    '#'-prefixed hex, given once for the game rather than per drive.
    """
    return espn.get_game_drives(event_id)
