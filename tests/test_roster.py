"""Offline tests for the roster row mapper.

`_player_row` is a pure function over a plain dict, so the shapes ESPN actually
sends — and the ones it omits — are exercised without touching the network. The
athlete dicts below are trimmed copies of live 2026 payloads.
"""

from dataglazer_nfl.clients.espn.roster import _player_row

DRAFTED = {
    "id": "4430802",
    "displayName": "Nick Bolton",
    "jersey": "32",
    "height": 71.0,
    "displayHeight": "5' 11\"",
    "weight": 232.0,
    "age": 26,
    "dateOfBirth": "2000-03-26T07:00Z",
    "birthPlace": {"city": "Frisco", "state": "TX", "country": "USA"},
    "experience": {"years": 5},
    "position": {"abbreviation": "LB", "displayName": "Linebacker"},
    "status": {"name": "Active"},
    "headshot": {"href": "https://a.espncdn.com/i/headshots/nfl/players/full/4430802.png"},
    "draft": {
        "displayText": "Year: 2021 Round: 2 Pick: 58",
        "round": 2,
        "year": 2021,
        "selection": 58,
    },
    "contract": {
        "salary": 15000000,
        "bonus": 0,
        "salaryRemaining": 15000000,
        "yearsRemaining": 1,
        "signedThrough": 2027,
    },
    "injuries": [],
    "rank": 1,
    "depth": [{"unit": "Base 4-3 D", "position": "WLB", "rank": 1, "slot": 1}],
}

# Undrafted, injured, and missing measurements — ESPN omits the keys entirely
# rather than sending nulls, which is the case that would raise if the mapper
# indexed instead of using .get().
UNDRAFTED = {
    "id": "634820",
    "displayName": "Jeff Caldwell",
    "position": {"abbreviation": "WR", "displayName": "Wide Receiver"},
    "status": {"name": "Day-To-Day"},
    "birthPlace": {"country": "Germany"},
    "injuries": [
        {
            "status": "Injured Reserve",
            "date": "2026-08-25T23:12Z",
            "shortComment": "Caldwell (knee) reverted to the Chiefs' injured reserve list.",
            "details": {
                "type": "Knee",
                "location": "Leg",
                "detail": "Soreness",
                "side": "Left",
                "returnDate": "2027-02-15",
            },
        }
    ],
}


def test_drafted_player_carries_full_biography():
    row = _player_row(DRAFTED, "KC")
    assert row["name"] == "Nick Bolton"
    assert row["team"] == "KC"
    assert row["position"] == "LB"
    assert row["birth_place"] == "Frisco, TX, USA"
    assert row["experience_years"] == 5
    assert row["draft"] == {
        "year": 2021,
        "round": 2,
        "pick": 58,
        "text": "Year: 2021 Round: 2 Pick: 58",
    }
    assert row["contract"]["salary"] == 15000000
    assert row["contract"]["signed_through"] == 2027
    assert row["headshot"].endswith("4430802.png")


def test_measurements_are_ints_not_floats():
    """ESPN sends 71.0 and 232.0; a chart label should not read "71.0"."""
    row = _player_row(DRAFTED, "KC")
    assert row["height_in"] == 71 and isinstance(row["height_in"], int)
    assert row["weight_lb"] == 232 and isinstance(row["weight_lb"], int)
    assert row["height"] == "5' 11\""


def test_healthy_player_has_no_injury():
    row = _player_row(DRAFTED, "KC")
    assert row["injuries"] == []
    assert row["injury_status"] is None


def test_undrafted_and_unmeasured_player_survives_missing_keys():
    row = _player_row(UNDRAFTED, "KC")
    assert row["draft"] is None
    assert row["contract"] is None
    assert row["height_in"] is None and row["weight_lb"] is None
    assert row["age"] is None and row["jersey"] is None
    # City and state absent; the country alone is still a birthplace.
    assert row["birth_place"] == "Germany"


def test_injury_detail_is_split_out_of_espns_two_levels():
    row = _player_row(UNDRAFTED, "KC")
    injury = row["injuries"][0]
    assert injury["type"] == "Knee"
    assert injury["location"] == "Leg"
    assert injury["detail"] == "Soreness"
    assert injury["side"] == "Left"
    assert injury["return_date"] == "2027-02-15"


def test_injury_status_is_hoisted_and_beats_roster_status():
    """`status` reads Day-To-Day for a player who is actually on season-ending IR."""
    row = _player_row(UNDRAFTED, "KC")
    assert row["status"] == "Day-To-Day"
    assert row["injury_status"] == "Injured Reserve"


def test_depth_is_omitted_not_nulled_when_excluded():
    """`rank: None` has to keep its one meaning: on the roster, off the chart."""
    with_depth = _player_row(DRAFTED, "KC", include_depth=True)
    assert with_depth["rank"] == 1
    assert with_depth["depth"][0]["position"] == "WLB"

    without = _player_row(DRAFTED, "KC", include_depth=False)
    assert "rank" not in without
    assert "depth" not in without
