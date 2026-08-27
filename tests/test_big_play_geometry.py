"""Field-map geometry on the big-play board.

The convention under test is that every yard line is expressed in the frame of
the team that *put the ball in play* — they attack toward 100. That is what
makes a return point backwards, and it is the thing the whole chart hangs on,
so it is pinned here against two real plays that between them cover the clean
case and the case where ESPN states no yard lines at all.

Offline: both payloads are committed under `tests/fixtures/` (see the README
there) and go in through the `summaries=` hook, so no network and no dependence
on the gitignored `data/cache/`.
"""

import gzip
import json
import pathlib

from dataglazer_nfl.clients.espn._field import ball_carrier
from dataglazer_nfl.clients.espn.weekly import get_big_play_board

FIXTURES = pathlib.Path(__file__).parent / "fixtures"

KINDS = {"pass", "run", "punt", "kick", "return", "lateral", "sack"}

# 2026 preseason week 3. A is a full play-by-play row, B a scoring-summary row.
COOK_PICK_SIX = "401873290"  # NO @ LAR
COWING_PUNT_RETURN = "401873285"  # SF @ LAC


def board(*event_ids, **kwargs):
    summaries = []
    for event_id in event_ids:
        with gzip.open(FIXTURES / f"{event_id}.json.gz") as fh:
            summaries.append(json.load(fh))
    kwargs.setdefault("include_returns", True)
    kwargs.setdefault("top_n", 50)
    return get_big_play_board(3, 2026, 1, summaries=summaries, **kwargs)


def one(event_id, needle, **kwargs):
    for play in board(event_id, **kwargs)["plays"]:
        if needle in play["text"]:
            return play
    raise AssertionError(f"no play matching {needle!r}")


# --- A. Cook 100-yard pick-six: every yard line stated in the text ---------


def test_pick_six_hinges_forward_then_all_the_way_back():
    play = one(COOK_PICK_SIX, "INTERCEPTED by A.Cook")
    assert play["segments"] == [
        {"from": 94, "to": 100, "kind": "pass", "by": "NO", "origin_source": "play_text"},
        {"from": 100, "to": 0, "kind": "return", "by": "LAR", "origin_source": "play_text"},
    ]


def test_pick_six_totals():
    play = one(COOK_PICK_SIX, "INTERCEPTED by A.Cook")
    assert play["yardage"] == 100  # ESPN's credited stat
    assert play["path_yards"] == 106  # 6-yard pass + 100-yard return
    assert play["net"] == -94  # the ball finished 94 yards behind the snap
    assert play["unit"] == "defense"


def test_pick_six_return_leg_belongs_to_the_defense():
    play = one(COOK_PICK_SIX, "INTERCEPTED by A.Cook")
    assert play["segments"][0]["by"] == "NO"
    assert play["segments"][1]["by"] == "LAR"
    assert play["team"] == "LAR"
    assert play["opponent"] == "NO"


# --- B. Cowing 83-yard punt return: no yard lines anywhere in the text -----


def test_punt_return_includes_the_kick_leg():
    play = one(COWING_PUNT_RETURN, "Jacob Cowing")
    assert play["segments"] == [
        {"from": 31, "to": 83, "kind": "punt", "by": "LAC", "origin_source": "play_text"},
        {"from": 83, "to": 0, "kind": "return", "by": "SF", "origin_source": "derived"},
    ]


def test_punt_leg_comes_out_a_plausible_length():
    # The sanity check on the back-solved catch point: if this isn't ~52, the
    # derivation is wrong, because no one punts 20 or 80 yards.
    punt = one(COWING_PUNT_RETURN, "Jacob Cowing")["segments"][0]
    assert punt["to"] - punt["from"] == 52


def test_punt_return_totals():
    play = one(COWING_PUNT_RETURN, "Jacob Cowing")
    assert play["yardage"] == 83
    assert play["path_yards"] == 135  # 52-yard punt + 83-yard return
    assert play["net"] == -31
    assert play["unit"] == "special_teams"


def test_derived_hinge_is_labelled_not_silent():
    play = one(COWING_PUNT_RETURN, "Jacob Cowing")
    assert play["segments"][1]["origin_source"] == "derived"
    assert board(COWING_PUNT_RETURN)["derived_count"] == 1


def test_derived_count_is_zero_when_every_hinge_was_stated():
    assert board(COOK_PICK_SIX)["derived_count"] == 0


# --- the contract ---------------------------------------------------------


def test_existing_keys_are_untouched():
    play = one(COOK_PICK_SIX, "INTERCEPTED by A.Cook")
    for key in ("event_id", "yardage", "text", "team", "type", "touchdown", "quarter"):
        assert key in play


def test_every_play_declares_its_frame():
    for play in board(COOK_PICK_SIX, COWING_PUNT_RETURN)["plays"]:
        assert play["frame"] == "snapping_team"


def test_labelling_fields_are_populated():
    play = one(COWING_PUNT_RETURN, "Jacob Cowing")
    assert play["player"] == "Jacob Cowing"
    assert play["game_name"] == "SF @ LAC"
    assert play["clock"]
    assert set(play["team_colors"]) == {"primary", "alternate"}
    assert play["team_colors"]["primary"].startswith("#")


def test_ball_carrier_reads_each_text_shape():
    assert (
        ball_carrier("Punt Return Touchdown", "Jacob Cowing 83 Yd Punt Return (E.Pineiro Kick)")
        == "Jacob Cowing"
    )
    assert (
        ball_carrier(
            "Pass Reception",
            "(Shotgun) B.Zappe pass short left to J.Bergen to PIT 28 for 44 yards",
        )
        == "J.Bergen"
    )
    assert (
        ball_carrier("Rushing Touchdown", "(Shotgun) J.Dobbs left end for 50 yards, TOUCHDOWN.")
        == "J.Dobbs"
    )
    assert (
        ball_carrier(
            "Pass Interception Return",
            "W.Howard pass short right INTERCEPTED by A.Cisco at NYJ 8.",
        )
        == "A.Cisco"
    )


def test_scrimmage_plays_are_a_single_forward_segment():
    seen = 0
    for play in board(COOK_PICK_SIX, COWING_PUNT_RETURN)["plays"]:
        if play["type"] not in {
            "Rush",
            "Rushing Touchdown",
            "Pass Reception",
            "Passing Touchdown",
        }:
            continue
        seen += 1
        assert len(play["segments"]) == 1
        assert play["net"] > 0, play["text"]
        assert play["unit"] == "offense"
    assert seen, "no scrimmage plays in the sample"


def test_every_return_points_backwards():
    seen = 0
    for play in board(COOK_PICK_SIX, COWING_PUNT_RETURN)["plays"]:
        if len(play["segments"]) != 2:
            continue
        seen += 1
        assert play["net"] < 0, play["text"]
        assert play["segments"][1]["kind"] == "return"
    assert seen, "no return plays in the sample"


def test_segments_are_well_formed_and_totals_agree():
    for play in board(COOK_PICK_SIX, COWING_PUNT_RETURN)["plays"]:
        segments = play["segments"]
        assert segments, play["text"]
        assert play["path_yards"] == sum(abs(s["to"] - s["from"]) for s in segments)
        assert play["net"] == segments[-1]["to"] - segments[0]["from"]
        for index, seg in enumerate(segments):
            assert seg["kind"] in KINDS
            assert seg["origin_source"] in {"play_text", "derived"}
            assert 0 <= seg["from"] <= 100 and 0 <= seg["to"] <= 100
            if index:  # chronological: each leg starts where the last ended
                assert seg["from"] == segments[index - 1]["to"]


def test_filters_still_work():
    assert len(board(COOK_PICK_SIX, top_n=2)["plays"]) == 2
    high = board(COOK_PICK_SIX, min_yards=60)["plays"]
    assert high and all(p["yardage"] >= 60 for p in high)
    assert not any(
        p["type"] == "Interception Return Touchdown"
        for p in board(COOK_PICK_SIX, include_returns=False)["plays"]
    )
