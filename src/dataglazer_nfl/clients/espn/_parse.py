"""Shared boxscore-payload helpers."""

from __future__ import annotations

from typing import Any


def _team_abbrs(game: dict[str, Any]) -> dict[str, str]:
    """{team_id: abbreviation} for the two teams in a game."""
    return {
        str(t["team"]["id"]): t["team"].get("abbreviation", "")
        for t in game.get("boxscore", {}).get("teams", [])
        if t.get("team", {}).get("id") is not None
    }


def _stat_groups(game: dict[str, Any], group: str):
    """Yield (team_abbr, labels, athletes) for one player stat group per team."""
    for team_block in game.get("boxscore", {}).get("players", []):
        abbr = team_block.get("team", {}).get("abbreviation", "")
        for stat_group in team_block.get("statistics", []):
            if stat_group.get("name") == group:
                yield abbr, stat_group.get("labels", []), stat_group.get("athletes", [])


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return default


def _all_plays(game: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten play-by-play.

    Plays live under drives.previous[].plays[], not at the top level of the
    summary response. Populated only once a game has started.
    """
    plays = []
    for drive in game.get("drives", {}).get("previous", []):
        plays.extend(drive.get("plays", []))
    if not plays:  # some endpoints/older payloads expose a flat list
        plays = game.get("plays", []) or []
    return plays
