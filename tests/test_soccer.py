"""Tests for the soccer plugin, with hand-computed expected values.

Reminder: the xG model here is an explicitly simplified/toy model (see
openscout/sports/soccer.py's module docstring), not a real calibrated one.
These tests check that our implementation matches *its own* documented
formula exactly -- not that it matches real-world shot conversion rates.
"""

from __future__ import annotations

import math

import pytest

from openscout.plugins import UnknownMetricError
from openscout.sports.soccer import (
    SoccerSport,
    action_threat,
    expected_goals,
    expected_goals_many,
    pass_completion_pct,
    total_threat_added,
    zone_value,
)


def _sigmoid(z: float) -> float:
    return 1 / (1 + math.exp(-z))


def test_expected_goals_open_play_foot_hand_computed():
    shot = {"distance": 11.0, "angle": 40.0, "body_part": "foot", "situation": "open_play"}
    z = -0.30 + -0.11 * 11.0 + 0.020 * 40.0
    assert expected_goals(shot) == pytest.approx(_sigmoid(z))
    assert expected_goals(shot) == pytest.approx(0.3295988401911314)


def test_expected_goals_header_is_penalized_relative_to_foot():
    foot_shot = {"distance": 11.0, "angle": 40.0, "body_part": "foot", "situation": "open_play"}
    head_shot = {"distance": 11.0, "angle": 40.0, "body_part": "head", "situation": "open_play"}
    assert expected_goals(head_shot) < expected_goals(foot_shot)
    assert expected_goals(head_shot) == pytest.approx(0.23866728515708963)


def test_expected_goals_penalty_is_fixed_value():
    assert expected_goals({"situation": "penalty"}) == pytest.approx(0.79)


def test_expected_goals_set_piece_and_counter_adjustments():
    base = {"distance": 20.0, "angle": 30.0, "body_part": "foot"}
    set_piece = expected_goals({**base, "situation": "set_piece"})
    counter = expected_goals({**base, "situation": "counter"})
    assert set_piece == pytest.approx(0.10909682119561293)
    assert counter == pytest.approx(0.14804719803168948)
    # a counter-attack shot should be rated more dangerous than a set piece
    # from the same distance/angle, per our documented adjustments.
    assert counter > set_piece


def test_expected_goals_closer_and_wider_is_always_more_dangerous():
    close = expected_goals({"distance": 6.0, "angle": 100.0, "situation": "open_play"})
    far = expected_goals({"distance": 30.0, "angle": 10.0, "situation": "open_play"})
    assert close > far


def test_expected_goals_rejects_unknown_body_part_and_situation():
    with pytest.raises(ValueError):
        expected_goals({"distance": 10, "angle": 10, "body_part": "flipper"})
    with pytest.raises(ValueError):
        expected_goals({"distance": 10, "angle": 10, "situation": "own_goal"})


def test_expected_goals_many_sums_totals():
    shots = [
        {"distance": 11.0, "angle": 40.0, "situation": "open_play"},
        {"situation": "penalty"},
    ]
    result = expected_goals_many(shots)
    assert result["shot_xg"] == [pytest.approx(0.3295988401911314), pytest.approx(0.79)]
    assert result["total_xg"] == pytest.approx(0.3295988401911314 + 0.79)


def test_pass_completion_pct_hand_computed():
    passes = [{"completed": True}] * 7 + [{"completed": False}] * 3
    assert pass_completion_pct(passes) == pytest.approx(70.0)


def test_pass_completion_pct_empty_is_zero():
    assert pass_completion_pct([]) == 0.0


def test_zone_value_hand_computed_at_goal_and_own_goal():
    # At the opponent's goal, distance is 0 so value is exactly 1.0.
    assert zone_value(100.0, 50.0) == pytest.approx(1.0)
    # Deep in your own half, value should be small but positive.
    assert zone_value(0.0, 50.0) == pytest.approx(0.06833852792409179)


def test_zone_value_monotonically_prefers_central_and_advanced_positions():
    assert zone_value(90.0, 50.0) > zone_value(50.0, 50.0) > zone_value(10.0, 50.0)
    # off to the side is worth less than the same depth centrally
    assert zone_value(90.0, 50.0) > zone_value(90.0, 5.0)


def test_action_threat_forward_pass_is_positive_backward_is_negative():
    forward = action_threat({"start_x": 40.0, "start_y": 50.0, "end_x": 90.0, "end_y": 50.0})
    backward = action_threat({"start_x": 90.0, "start_y": 50.0, "end_x": 40.0, "end_y": 50.0})
    assert forward > 0
    assert backward < 0
    assert forward == pytest.approx(-backward)


def test_total_threat_added_sums_actions():
    actions = [
        {"start_x": 10.0, "start_y": 50.0, "end_x": 50.0, "end_y": 50.0},
        {"start_x": 50.0, "start_y": 50.0, "end_x": 90.0, "end_y": 50.0},
    ]
    result = total_threat_added(actions)
    assert result["total_xt"] == pytest.approx(sum(result["action_xt"]))
    assert len(result["action_xt"]) == 2


def test_soccer_sport_plugin_metadata_and_dispatch():
    sport = SoccerSport()
    assert sport.name == "soccer"
    assert set(sport.list_metrics()) == {"xg", "pass_pct", "xt_added"}
    shot = {"distance": 11.0, "angle": 40.0, "situation": "open_play"}
    assert sport.compute("xg", shot) == pytest.approx(expected_goals(shot))


def test_soccer_sport_unknown_metric_raises():
    sport = SoccerSport()
    with pytest.raises(UnknownMetricError):
        sport.compute("nope", [])
