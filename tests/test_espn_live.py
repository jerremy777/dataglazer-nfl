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


def test_roster_carries_biography_for_every_player():
    rows = espn.get_team_players(12)
    assert 80 <= len(rows) <= 100
    assert all(r["height_in"] and r["weight_lb"] for r in rows)
    assert {r["position"] for r in rows} >= {"QB", "WR", "CB"}
    # Roughly half a roster is undrafted and many carry no contract, so these
    # assert the fields arrive at all rather than that everyone has them.
    assert any(r["draft"] for r in rows)
    assert any(r["contract"] for r in rows)
    # ESPN has no photo for the newest rookies — 87/95 on this roster.
    assert sum(1 for r in rows if r["headshot"]) > len(rows) * 0.75


def test_roster_depth_join_covers_the_whole_roster():
    rows = espn.get_team_players(12)
    assert any(r["rank"] == 1 for r in rows)
    assert all("rank" in r and "depth" in r for r in rows)


def test_injuries_accept_a_team_name_not_just_an_id():
    """The depth-chart endpoint 404s on anything but a numeric ID, so the name
    has to be resolved in the client — not only in the MCP tool."""
    rows = espn.get_team_injuries("KC")
    assert rows
    assert all(r["team"] == "KC" for r in rows)
    assert all("rank" in r and "depth" in r for r in rows)


def test_injury_rows_carry_height_and_weight():
    """Keyed as `get_team_players` keys them, so the two can be joined."""
    rows = espn.get_team_injuries("KC")
    assert all(r["height_in"] and r["weight_lb"] for r in rows)
    assert all(isinstance(r["height_in"], int) for r in rows)
    assert all(r["height"].startswith(("5", "6", "7")) for r in rows)

    roster = {r["name"]: r for r in espn.get_team_players("KC")}
    for row in rows:
        player = roster[row["name"]]
        assert (row["height_in"], row["weight_lb"]) == (
            player["height_in"],
            player["weight_lb"],
        )
