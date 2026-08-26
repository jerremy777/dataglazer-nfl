"""Team colours, normalised to '#'-prefixed hex ready for matplotlib or CSS."""

from __future__ import annotations

from typing import Any

# Fallback when a team's alternateColor is missing or duplicates its primary.
_LIGHT_FALLBACK = "#FFFFFF"
_DARK_FALLBACK = "#000000"


def _hex_color(value: Any) -> str | None:
    """Normalise an ESPN colour ('0085ca') to CSS/matplotlib form ('#0085CA')."""
    text = str(value or "").strip().lstrip("#")
    if len(text) != 6:
        return None
    try:
        int(text, 16)
    except ValueError:
        return None
    return "#" + text.upper()


def _contrasting(primary: str) -> str:
    """Pick black or white — whichever reads against `primary`."""
    r, g, b = (int(primary[i : i + 2], 16) for i in (1, 3, 5))
    # Rec. 601 luma; the 0.5 cut is the usual "is this a dark brand colour" line.
    luma = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return _DARK_FALLBACK if luma > 0.5 else _LIGHT_FALLBACK


def get_team_colors(game: dict[str, Any]) -> dict[str, dict[str, str]]:
    """{team_abbr: {primary, alternate}} for the two teams, '#'-prefixed.

    ESPN stores brand colours as bare hex ('0085ca'). Both keys are always
    present: when `alternateColor` is missing, malformed, or identical to
    `color`, `alternate` falls back to black or white by contrast, so callers
    never have to null-check before handing these to matplotlib or CSS.
    """
    colors: dict[str, dict[str, str]] = {}
    for block in game.get("boxscore", {}).get("teams", []):
        team = block.get("team", {})
        abbr = team.get("abbreviation")
        if not abbr:
            continue
        primary = _hex_color(team.get("color")) or _DARK_FALLBACK
        alternate = _hex_color(team.get("alternateColor"))
        if alternate is None or alternate == primary:
            alternate = _contrasting(primary)
        colors[abbr] = {"primary": primary, "alternate": alternate}
    return colors
