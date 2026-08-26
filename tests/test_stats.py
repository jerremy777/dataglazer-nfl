"""Pure stat maths — no network."""

import pytest

from dataglazer_nfl.clients.espn._parse import _to_int
from dataglazer_nfl.clients.espn.weekly import nfl_passer_rating


def test_perfect_passer_rating_is_capped():
    # The formula's components each cap at 2.375, giving a 158.3 ceiling.
    assert nfl_passer_rating(20, 20, 400, 5, 0) == pytest.approx(158.3, abs=0.05)


def test_zero_attempts_does_not_divide_by_zero():
    assert nfl_passer_rating(0, 0, 0, 0, 0) == 0


def test_known_stat_line():
    # 20/30, 300 yds, 2 TD, 1 INT. Components: 1.8333 / 1.75 / 1.3333 / 1.5417,
    # summed, divided by 6, times 100.
    assert nfl_passer_rating(20, 30, 300, 2, 1) == pytest.approx(107.64, abs=0.05)


@pytest.mark.parametrize(
    "raw,expected",
    [("1,234", 1234), (" 7 ", 7), ("", 0), (None, 0), ("--", 0), (12, 12)],
)
def test_to_int_survives_espn_formatting(raw, expected):
    assert _to_int(raw) == expected


def test_to_int_honours_default():
    assert _to_int("n/a", default=-1) == -1
