"""Colour normalisation and contrast — no network."""

import pytest

from dataglazer_nfl.clients.espn.colors import _contrasting, _hex_color


@pytest.mark.parametrize(
    "raw,expected",
    [("0085ca", "#0085CA"), ("#0085ca", "#0085CA"), (" 0085CA ", "#0085CA")],
)
def test_hex_color_normalises(raw, expected):
    assert _hex_color(raw) == expected


@pytest.mark.parametrize("bad", ["", None, "xyz", "12345", "1234567", "gggggg"])
def test_hex_color_rejects_junk(bad):
    assert _hex_color(bad) is None


def test_contrasting_picks_readable_foreground():
    assert _contrasting("#FFFFFF") == "#000000"  # light brand -> dark text
    assert _contrasting("#000000") == "#FFFFFF"  # dark brand  -> light text


def test_contrasting_output_is_always_a_valid_hex():
    for brand in ("#0085CA", "#E31837", "#FFB612", "#203731"):
        assert _hex_color(_contrasting(brand)) is not None
