"""Single-game tools: scoring summary and drive log."""

from __future__ import annotations

from typing import Any

from ._parse import _team_abbrs, _to_int
from .colors import get_team_colors
from .schedule import get_game_summary, is_completed


def _game_teams(game: dict[str, Any]) -> tuple[dict[str, str], dict[str, int], bool]:
    """({home/away: abbr}, {abbr: final_score}, completed) from the header."""
    comp = (game.get("header", {}).get("competitions") or [{}])[0]
    side: dict[str, str] = {}
    final: dict[str, int] = {}
    for competitor in comp.get("competitors", []):
        abbr = competitor.get("team", {}).get("abbreviation")
        if not abbr:
            continue
        side[competitor.get("homeAway", "")] = abbr
        final[abbr] = _to_int(competitor.get("score"))
    return side, final, is_completed(game)


def _matchup_name(game: dict[str, Any]) -> str:
    side, _, _ = _game_teams(game)
    return f"{side.get('away', '')} @ {side.get('home', '')}".strip(" @")


def _drives_in_order(game: dict[str, Any]) -> list[dict[str, Any]]:
    """Every drive, chronological — `previous` plus `current` if the game is live."""
    drives = list(game.get("drives", {}).get("previous", []))
    current = game.get("drives", {}).get("current")
    if current:
        drives.append(current)
    return drives


# Scoring-play classification. ESPN's `type.text` is the primary signal; the
# play text disambiguates the cases where one type covers two units (a fumble
# recovered on a kickoff is typed "Fumble Return Touchdown" but is a
# special-teams score).
_OFFENSE_SCORE_TYPES = {
    "Rushing Touchdown",
    "Passing Touchdown",
    "Field Goal Good",
    "Extra Point Good",
    "Two-Point Conversion",
    "Two-Point Rush Good",
    "Two-Point Pass Good",
    "Fumble Recovery (Own) Touchdown",
}

_DEFENSE_SCORE_TYPES = {
    "Interception Return Touchdown",
    "Fumble Return Touchdown",
    "Fumble Recovery (Opponent) Touchdown",
    "Sack Opp Fumble Recovery",
    "Safety",
    "Defensive 2pt Conversion",
}

_SPECIAL_TEAMS_SCORE_TYPES = {
    "Punt Return Touchdown",
    "Kickoff Return Touchdown",
    "Blocked Punt Touchdown",
    "Blocked Field Goal Touchdown",
    "Blocked Field Goal",
    "Blocked Punt",
    "Missed Field Goal Return",
}

# Words that mean the ball got there via a kicking play, whatever ESPN typed it.
_SPECIAL_TEAMS_MARKERS = ("punt", "kickoff", "kicks", "blocked", "onside", "free kick")

CATEGORIES = ("offense", "defense", "special_teams")


def classify_scoring_play(
    play_type: str,
    play_text: str,
    scoring_team: str,
    possessing_team: str | None,
) -> str:
    """Return 'offense', 'defense' or 'special_teams' for one scoring play.

    `possessing_team` is the team on offense at the snap. It is only used as a
    fallback for play types not seen in the reference data — it cannot be the
    primary signal because ESPN lists the *receiving* team as the "offense"
    participant on a kickoff, which would file a kick-return touchdown under
    offence.
    """
    text = (play_text or "").lower()
    special = any(marker in text for marker in _SPECIAL_TEAMS_MARKERS)

    if play_type in _SPECIAL_TEAMS_SCORE_TYPES:
        return "special_teams"
    if play_type in _DEFENSE_SCORE_TYPES:
        # A fumble recovered on a punt or kickoff is a special-teams score even
        # though ESPN types it as a fumble return.
        if "fumble" in play_type.lower() and special:
            return "special_teams"
        if play_type == "Safety" and special:
            return "special_teams"
        return "defense"
    if play_type in _OFFENSE_SCORE_TYPES:
        return "offense"

    # Unknown type (ESPN adds them occasionally). Points scored by the team that
    # did not have the ball are never offensive; kicking-play wording then
    # separates special teams from defence.
    if "safety" in text:
        return "special_teams" if special else "defense"
    if possessing_team and scoring_team != possessing_team:
        return "special_teams" if special else "defense"
    return "special_teams" if special else "offense"


def get_game_scoring_summary(
    event_id: str | int,
    strict: bool = True,
    game: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Every scoring play in one game, split by offence / defence / special teams.

    Points come from the change in ESPN's running score across consecutive
    scoring plays, not from a per-play-type point table. ESPN folds the try into
    the touchdown play — "…TOUCHDOWN. T.Loop extra point is GOOD" is one play
    worth 7 — and there are no separate extra-point or two-point scoring plays
    to add, so a fixed 6/3/1/2 table under-counts every converted touchdown. The
    running score also absorbs missed extra points (6) and two-point tries (8)
    for free, which is what makes the rollup reconcile to the final score.

    The scoring team likewise comes from *which side's* score moved, not from
    the drive's team: a pick-six or a punt-return touchdown is recorded inside
    the drive of the team that lost the ball, so crediting the drive's team
    credits the wrong side of a non-offensive score.

    Args:
        event_id: ESPN event ID, as returned by `get_week_events`.
        strict: Raise if a finished game's category split does not add up to the
            official final score. Set False to get the numbers plus `warnings`.
        game: A summary payload to use instead of refetching.

    Returns {event_id, name, completed, scoring_plays, team_totals, team_colors,
    final_score, reconciles, warnings}, where each scoring play is
    {team, quarter, clock, points, category, play_type, description} and
    team_totals is {team: {offense_points, defense_points, special_teams_points,
    total_points}}.
    """
    if game is None:
        game = get_game_summary(event_id)

    side, final, completed = _game_teams(game)
    colors = get_team_colors(game)
    warnings: list[str] = []

    totals = {abbr: {f"{c}_points": 0 for c in CATEGORIES} | {"total_points": 0} for abbr in final}

    scoring_plays: list[dict[str, Any]] = []
    away_score = home_score = 0

    for drive in _drives_in_order(game):
        for play in drive.get("plays", []):
            if not play.get("scoringPlay"):
                continue
            away = _to_int(play.get("awayScore"), away_score)
            home = _to_int(play.get("homeScore"), home_score)
            delta_away, delta_home = away - away_score, home - home_score
            away_score, home_score = away, home

            if delta_away > 0 and delta_home > 0:
                warnings.append(f"Both teams gained points on play {play.get('id')}; skipped.")
                continue
            if delta_away <= 0 and delta_home <= 0:
                warnings.append(f"Scoring play {play.get('id')} moved no score; skipped.")
                continue

            team = side["away"] if delta_away > 0 else side["home"]
            points = max(delta_away, delta_home)
            play_type = (play.get("type") or {}).get("text", "")
            text = play.get("text", "")
            possessing = (play.get("start", {}).get("team") or {}).get("id")
            possessing_abbr = None
            if possessing is not None:
                possessing_abbr = _team_abbrs(game).get(str(possessing))

            category = classify_scoring_play(play_type, text, team, possessing_abbr)

            scoring_plays.append(
                {
                    "team": team,
                    "quarter": (play.get("period") or {}).get("number"),
                    "clock": (play.get("clock") or {}).get("displayValue"),
                    "points": points,
                    "category": category,
                    "play_type": play_type,
                    "description": text,
                }
            )

            if team in totals:
                totals[team][f"{category}_points"] += points
                totals[team]["total_points"] += points

    # The split partitions the points, so this can only fail on a bad payload.
    for abbr, row in totals.items():
        split = sum(row[f"{c}_points"] for c in CATEGORIES)
        if split != row["total_points"]:
            warnings.append(
                f"{abbr}: category split {split} != tallied total {row['total_points']}."
            )
        if abbr in final and row["total_points"] != final[abbr]:
            warnings.append(
                f"{abbr}: scoring plays total {row['total_points']} but ESPN's "
                f"final score is {final[abbr]}."
            )

    reconciles = not warnings
    if strict and completed and not reconciles:
        raise ValueError(
            f"Scoring summary for event {event_id} does not reconcile to the "
            f"final score: " + " ".join(warnings)
        )

    return {
        "event_id": str(event_id),
        "name": _matchup_name(game),
        "completed": completed,
        "scoring_plays": scoring_plays,
        "team_totals": totals,
        "team_colors": colors,
        "final_score": final,
        "reconciles": reconciles,
        "warnings": warnings,
    }


def get_game_drives(
    event_id: str | int,
    game: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Drive-by-drive log for one game.

    One row per possession, in order, which is a far easier unit to chart than
    raw play-by-play — "which drives produced points" is a filter on `is_score`
    rather than a scan of every snap. `team` here is the team with the ball, so
    on a drive that ended in a pick-six the row belongs to the team that threw
    it; use `get_game_scoring_summary` for who actually scored.

    Args:
        event_id: ESPN event ID, as returned by `get_week_events`.
        game: A summary payload to use instead of refetching.

    Returns {event_id, name, completed, drives, team_colors}, where each drive is
    {team, quarter_started, description, result, result_detail, yards, plays,
    time_of_possession, is_score}.
    """
    if game is None:
        game = get_game_summary(event_id)

    _, _, completed = _game_teams(game)
    drives = []
    for drive in _drives_in_order(game):
        drives.append(
            {
                "team": drive.get("team", {}).get("abbreviation", ""),
                "quarter_started": ((drive.get("start", {}).get("period") or {}).get("number")),
                "description": drive.get("description", ""),
                # ESPN's short code ("DOWNS", "SF") plus its spelled-out form.
                "result": drive.get("result") or drive.get("shortDisplayResult") or "",
                "result_detail": drive.get("displayResult", ""),
                "yards": drive.get("yards"),
                "plays": drive.get("offensivePlays"),
                "time_of_possession": (drive.get("timeElapsed") or {}).get("displayValue"),
                "is_score": bool(drive.get("isScore")),
            }
        )

    return {
        "event_id": str(event_id),
        "name": _matchup_name(game),
        "completed": completed,
        "drives": drives,
        "team_colors": get_team_colors(game),
    }
