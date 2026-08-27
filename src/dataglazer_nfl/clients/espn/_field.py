"""Field-map geometry for the big-play board.

Turns one ESPN play into a list of segments on a single 0-100 field, so a chart
script can draw the play as a path without parsing `text` itself.

**The frame is the team that put the ball in play.** They attack toward 100; 0
is the goal line they defend. On a kickoff, where nobody snaps it, the kicking
team takes that role, so kick and punt returns behave like every other return.
Under this convention direction carries meaning: explosive offensive plays run
left to right, and interception, fumble, punt and kick returns run right to
left with a negative `net`. A pick-six is then a short forward stub hinged into
a long backward sweep, readable as a pick-six before any colour or label.

Note the rule is really "possession changed", not "the defense did it" — a sack
or tackle for loss also points left. That is harmless on a board with a
20-yard floor, but the direction annotation is only safe while it stays
explosives-only.

Three ESPN fields look like they answer this and do not:

- `statYardage` is the *return* distance on an interception or kick and the kick
  distance on a field goal, never net movement. It is used here only to
  back-solve a catch point that ESPN omitted (see `origin_source`).
- `yardsToEndzone` is measured against different teams at the start and end of
  any play where possession changed, and is mirrored on punts.
- `yardLine` *is* usable: it is absolute 0-100 with the **home team defending 0
  and attacking 100**, fixed for the whole game. Everything here is normalised
  out of that frame and into the snapping team's.
"""

from __future__ import annotations

import re
from typing import Any

# Play text uses NFL gamebook abbreviations, which are not the abbreviations on
# the team object: "INTERCEPTED by A.Cook at LA 0" in a game ESPN calls LAR.
_ABBR_ALIASES = {
    "ARZ": "ARI",
    "BLT": "BAL",
    "CLV": "CLE",
    "HST": "HOU",
    "LA": "LAR",
    "WAS": "WSH",
}

_TAKEAWAY_SPOT = re.compile(
    r"(?:INTERCEPTED|RECOVERED|recovered) by .{0,40}?"
    r"(?:\s+(?:ob|in the end zone))?\s+at\s+([A-Z]{2,3})\s*(-?\d{1,2})"
)
# "punts 51 yards to DAL 26", "kicks 61 yards from PIT 35 to NYJ 4"
_KICK_SPOT = re.compile(
    r"(?:punts|kicks)\s+\d+\s+yards\s+(?:from\s+[A-Z]{2,3}\s*-?\d{1,2}\s+)?to\s+([A-Z]{2,3})\s*(-?\d{1,2})"
)

# "Jacob Cowing 83 Yd Punt Return (Eddy Pineiro Kick)" — a scoring-summary row
# with no yard lines anywhere in it.
_SUMMARY_ROW = re.compile(r"^(.+?)\s+\d+\s+Yd\s+", re.IGNORECASE)
_RETURNER = re.compile(r"(?:INTERCEPTED|RECOVERED|recovered) by (?:[A-Z]{2,3}-)?([A-Z][\w'.-]+)")
_RECEIVER = re.compile(
    r"pass(?:\s+(?:short|deep))?(?:\s+(?:left|right|middle))?\s+to\s+([A-Z][\w'.-]+)"
)
_RUSHER = re.compile(r"^(?:\([^)]*\)\s*)?([A-Z][\w'.-]+)")

INTERCEPTION_TYPES = {"Pass Interception Return", "Interception Return Touchdown"}
FUMBLE_RETURN_TYPES = {"Fumble Return Touchdown", "Fumble Recovery (Opponent)"}
PUNT_RETURN_TYPES = {"Punt Return Touchdown"}
KICK_RETURN_TYPES = {"Kickoff Return Touchdown"}
RETURN_TYPES = INTERCEPTION_TYPES | FUMBLE_RETURN_TYPES | PUNT_RETURN_TYPES | KICK_RETURN_TYPES

PLAY_TEXT = "play_text"
DERIVED = "derived"


def frame_from_sides(side: dict[str, str]) -> dict[str, int]:
    """{abbr: +1 | -1} — which way each team moves along ESPN's absolute yardline."""
    frame: dict[str, int] = {}
    if side.get("home"):
        frame[side["home"]] = 1
    if side.get("away"):
        frame[side["away"]] = -1
    return frame


def normalise(yard: Any, direction: int | None) -> int | None:
    """An absolute yardline into the frame of a team attacking `direction`."""
    if yard is None or direction is None:
        return None
    return yard if direction == 1 else 100 - yard


def _spot(match: re.Match[str] | None, frame: dict[str, int], direction: int) -> int | None:
    """A matched "TEAM NN" label to a yardline in the snapping team's frame."""
    if not match:
        return None
    abbr = _ABBR_ALIASES.get(match.group(1), match.group(1))
    own = frame.get(abbr)
    if own is None:
        return None
    # The label counts yards from the goal line that team defends.
    absolute = int(match.group(2)) if own == 1 else 100 - int(match.group(2))
    return normalise(max(0, min(100, absolute)), direction)


def ball_carrier(play_type: str, text: str) -> str:
    """The player who finished with the ball, for the arrow label."""
    summary = _SUMMARY_ROW.match(text.strip())
    if summary:  # "Jacob Cowing 83 Yd Punt Return (...)"
        return summary.group(1).strip()
    if play_type in RETURN_TYPES:
        returner = _RETURNER.search(text)
        if returner:
            return returner.group(1)
    if "pass" in text.lower():
        receiver = _RECEIVER.search(text)
        if receiver:
            return receiver.group(1)
    rusher = _RUSHER.match(text.strip())
    return rusher.group(1) if rusher else ""


def _first_leg_kind(play_type: str, text: str) -> str:
    if play_type in PUNT_RETURN_TYPES:
        return "punt"
    if play_type in KICK_RETURN_TYPES:
        return "kick"
    if play_type in INTERCEPTION_TYPES or "pass" in text.lower():
        return "pass"
    return "run"


def play_segments(
    play: dict[str, Any],
    direction: int,
    frame: dict[str, int],
    snapper: str,
    other: str,
) -> list[dict[str, Any]]:
    """Chronological legs of one play, in the snapping team's frame.

    A play from scrimmage is one segment. Anything where the ball changed hands
    is two: the leg that got it there, hinged into the return.
    """
    play_type = (play.get("type") or {}).get("text", "")
    text = play.get("text") or ""
    start = normalise((play.get("start") or {}).get("yardLine"), direction)
    end = normalise((play.get("end") or {}).get("yardLine"), direction)
    if start is None or end is None:
        return []

    if play_type not in RETURN_TYPES:
        kind = "lateral" if "Lateral" in text else _first_leg_kind(play_type, text)
        return [
            {
                "from": start,
                "to": end,
                "kind": "pass" if kind == "pass" else kind,
                "by": snapper,
                "origin_source": PLAY_TEXT,
            }
        ]

    # Where the ball changed hands. Stated in the play description on a full
    # play-by-play row; absent entirely on a scoring-summary row.
    if play_type in PUNT_RETURN_TYPES | KICK_RETURN_TYPES:
        hinge = _spot(_KICK_SPOT.search(text), frame, direction)
    else:
        hinge = _spot(_TAKEAWAY_SPOT.search(text), frame, direction)

    hinge_source = PLAY_TEXT
    if hinge is None:
        # Back-solve it: statYardage is the return distance, and the return runs
        # backwards in this frame, so the ball was caught that far beyond where
        # it finished. This is an inference, and it gets labelled as one.
        credited = play.get("statYardage")
        if credited is None:
            return []
        hinge = max(0, min(100, end + credited))
        hinge_source = DERIVED

    return [
        {
            "from": start,
            "to": hinge,
            "kind": _first_leg_kind(play_type, text),
            "by": snapper,
            "origin_source": PLAY_TEXT,
        },
        {
            "from": hinge,
            "to": end,
            "kind": "return",
            "by": other,
            "origin_source": hinge_source,
        },
    ]


def path_yards(segments: list[dict[str, Any]]) -> int:
    """Ground the ball actually covered — the punt leg counts as well as the return."""
    return sum(abs(seg["to"] - seg["from"]) for seg in segments)


def net_yards(segments: list[dict[str, Any]]) -> int:
    """Signed displacement across the whole play. Negative on every return."""
    return segments[-1]["to"] - segments[0]["from"]
