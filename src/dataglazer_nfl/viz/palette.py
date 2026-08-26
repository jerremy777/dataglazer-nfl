"""Named colours for the @dataglazer theme.

The structural tokens are parsed out of `dataglazer.mplstyle` rather than
retyped, so editing the stylesheet moves the charts with it. The series colours
come from that file's `axes.prop_cycle`; the extra shades below are chart-local
tints of the same system that matplotlib has no rcParam for.
"""

from __future__ import annotations

import re

from dataglazer_nfl.config import STYLE_FILE


def _rc() -> dict[str, str]:
    values: dict[str, str] = {}
    for line in STYLE_FILE.read_text().splitlines():
        line = line.split("#")[0] if not line.strip().startswith("#") else ""
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        values[key.strip()] = val.strip()
    return values


def _hex(value: str) -> str:
    value = value.strip().lstrip("#")
    return f"#{value.upper()}"


_RC = _rc()

# Structural tokens, straight from the stylesheet.
BG = _hex(_RC["figure.facecolor"])  # page / figure background
SURFACE = _hex(_RC["axes.facecolor"])  # plot area
BORDER = _hex(_RC["axes.edgecolor"])
GRID = _hex(_RC["grid.color"])
TEXT = _hex(_RC["axes.labelcolor"])
MUTED = _hex(_RC["xtick.color"])

# Series colours, in stylesheet order.
CYCLE = [_hex(c) for c in re.findall(r"'([0-9A-Fa-f]{6})'", _RC["axes.prop_cycle"])]
CYAN, RED, GOLD, ORANGE, PURPLE = CYCLE

# Chart-local shades with no rcParam equivalent.
SPINE = "#3A4854"
TICK_BRIGHT = "#E6EDF3"
TICK_SUB = "#8FD4EE"
FOOTNOTE = "#7C8B99"

__all__ = [
    "BG",
    "BORDER",
    "CYAN",
    "CYCLE",
    "FOOTNOTE",
    "GOLD",
    "GRID",
    "MUTED",
    "ORANGE",
    "PURPLE",
    "RED",
    "SPINE",
    "SURFACE",
    "TEXT",
    "TICK_BRIGHT",
    "TICK_SUB",
]
