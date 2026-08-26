"""Integration tests against the live ESPN API.

Deselected by default: `pytest -m "not network"`.
"""

import pytest

from dataglazer_nfl.clients import espn

WEEK, YEAR = 1, 2025

pytestmark = pytest.mark.network


def test_week_one_has_sixteen_games():
    games = espn.get_week_events(WEEK, YEAR)
    assert len(games) == 16
    assert all(g["completed"] for g in games)


def test_efficiency_leaders_are_sorted_and_plausible():
    rows = espn.get_efficiency_leaders(WEEK, YEAR)
    assert rows
    ratings = [r["rating"] for r in rows]
    assert ratings == sorted(ratings, reverse=True)
    assert all(0 <= r <= 158.3 for r in ratings)


def test_turnover_differentials_sum_to_zero():
    """Every game contributes two rows, so the week nets out."""
    rows = espn.get_turnover_tracker(WEEK, YEAR)
    assert len(rows) == 32
    assert sum(r["diff"] for r in rows) == 0


def test_scoring_summary_reconciles_with_the_final_score():
    event_id = espn.get_week_events(WEEK, YEAR)[0]["id"]
    summary = espn.get_game_scoring_summary(event_id)
    assert summary["reconciles"], summary["warnings"]
    for team, totals in summary["team_totals"].items():
        parts = (
            totals["offense_points"] + totals["defense_points"] + totals["special_teams_points"]
        )
        assert parts == totals["total_points"] == summary["final_score"][team]


def test_team_colors_are_matplotlib_ready():
    event_id = espn.get_week_events(WEEK, YEAR)[0]["id"]
    colors = espn.get_game_drives(event_id)["team_colors"]
    for pair in colors.values():
        assert pair["primary"].startswith("#") and len(pair["primary"]) == 7
        assert pair["alternate"] != pair["primary"]
