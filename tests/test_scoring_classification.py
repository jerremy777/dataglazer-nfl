"""Scoring-play classification — the logic most specific to this project.

The tricky case is that ESPN files a defensive score inside the *losing*
team's drive, so the possessing team is the wrong side exactly when it matters.
"""

from dataglazer_nfl.clients.espn.games import CATEGORIES, classify_scoring_play


def classify(play_type, text, scoring, possessing):
    return classify_scoring_play(play_type, text, scoring, possessing)


def test_offensive_touchdown():
    assert classify("Passing Touchdown", "P.Mahomes pass to T.Kelce", "KC", "KC") == "offense"


def test_rushing_touchdown():
    assert classify("Rushing Touchdown", "I.Pacheco up the middle", "KC", "KC") == "offense"


def test_pick_six_is_defense_not_offense():
    # Filed under the drive of the team that threw it — possessing != scoring.
    assert (
        classify("Interception Return Touchdown", "L.Sneed 42 yd return", "KC", "BUF") == "defense"
    )


def test_punt_return_touchdown_is_special_teams():
    got = classify("Punt Return Touchdown", "M.Hardman 68 yd punt return", "KC", "BUF")
    assert got == "special_teams"


def test_made_field_goal_counts_as_offense():
    """Deliberate: a made FG is the product of the drive that set it up.

    Only kicks that go wrong — blocks and returns — move to special teams, so
    that the special-teams column means "points the kicking game created",
    not "points a kicker scored".
    """
    assert classify("Field Goal Good", "H.Butker 45 yd field goal", "KC", "KC") == "offense"


def test_blocked_field_goal_return_is_special_teams():
    got = classify("Blocked Field Goal Touchdown", "J.Reid 30 yd return", "KC", "BUF")
    assert got == "special_teams"


def test_every_result_is_a_known_category():
    samples = [
        ("Passing Touchdown", "pass", "KC", "KC"),
        ("Fumble Return Touchdown", "return", "KC", "BUF"),
        ("Blocked Punt Touchdown", "blocked punt", "KC", "BUF"),
        ("Safety", "tackled in end zone", "KC", "BUF"),
        ("", "", "KC", None),
    ]
    for args in samples:
        assert classify(*args) in CATEGORIES
