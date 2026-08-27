"""Tests for the basketball plugin, with hand-computed expected values."""

from __future__ import annotations

import pytest

from openscout.sports.basketball import (
    BasketballSport,
    effective_fg_pct,
    four_factors,
    per_lite,
    true_shooting_pct,
)


def test_true_shooting_pct_hand_computed():
    # TS% = PTS / (2 * (FGA + 0.44*FTA))
    # 25 / (2 * (18 + 0.44*6)) = 25 / (2 * 20.64) = 25 / 41.28
    box = {"pts": 25, "fga": 18, "fta": 6}
    assert true_shooting_pct(box) == pytest.approx(25 / (2 * (18 + 0.44 * 6)))
    assert true_shooting_pct(box) == pytest.approx(0.6056201550387597)


def test_true_shooting_pct_zero_attempts_is_zero_not_error():
    assert true_shooting_pct({"pts": 0, "fga": 0, "fta": 0}) == 0.0


def test_effective_fg_pct_hand_computed():
    # eFG% = (FG + 0.5*FG3) / FGA = (10 + 0.5*3) / 20 = 11.5 / 20
    box = {"fg": 10, "fg3": 3, "fga": 20}
    assert effective_fg_pct(box) == pytest.approx(0.575)


def test_effective_fg_pct_zero_attempts_is_zero():
    assert effective_fg_pct({"fg": 0, "fg3": 0, "fga": 0}) == 0.0


def test_four_factors_hand_computed():
    box = {"fga": 20, "fta": 10, "tov": 15, "orb": 10, "opp_drb": 30, "fg": 8, "fg3": 2}
    result = four_factors(box)
    assert result["efg_pct"] == pytest.approx(0.45)
    assert result["tov_pct"] == pytest.approx(15 / (20 + 0.44 * 10 + 15))
    assert result["orb_pct"] == pytest.approx(0.25)
    assert result["ft_rate"] == pytest.approx(0.5)


def test_four_factors_requires_opp_drb():
    with pytest.raises(ValueError, match="opp_drb"):
        four_factors({"fga": 10, "fta": 2, "tov": 1, "orb": 3, "fg": 4, "fg3": 1})


def test_four_factors_aggregates_a_list_of_box_scores():
    rows = [
        {"fga": 10, "fta": 5, "tov": 5, "orb": 5, "opp_drb": 10, "fg": 4, "fg3": 1},
        {"fga": 10, "fta": 5, "tov": 10, "orb": 5, "opp_drb": 20, "fg": 4, "fg3": 1},
    ]
    result = four_factors(rows)
    totals_fga, totals_fta, totals_tov = 20, 10, 15
    totals_orb, totals_opp_drb = 10, 30
    assert result["tov_pct"] == pytest.approx(
        totals_tov / (totals_fga + 0.44 * totals_fta + totals_tov)
    )
    assert result["orb_pct"] == pytest.approx(totals_orb / (totals_orb + totals_opp_drb))


def test_per_lite_hand_computed():
    box = {
        "pts": 20, "fg": 8, "fga": 20, "fta": 10, "ft": 6,
        "orb": 10, "drb": 5, "stl": 2, "ast": 4, "blk": 1, "pf": 3, "tov": 15,
    }
    expected = (
        20 + 0.4 * 8 - 0.7 * 20 - 0.4 * (10 - 6)
        + 0.7 * 10 + 0.3 * 5 + 2 + 0.7 * 4 + 0.7 * 1 - 0.4 * 3 - 15
    )
    assert per_lite(box) == pytest.approx(expected)
    assert per_lite(box) == pytest.approx(5.4)


def test_basketball_sport_plugin_metadata_and_dispatch():
    sport = BasketballSport()
    assert sport.name == "basketball"
    metrics = sport.list_metrics()
    assert set(metrics) == {"ts_pct", "efg_pct", "four_factors", "per_lite"}

    box = {"pts": 25, "fga": 18, "fta": 6}
    assert sport.compute("ts_pct", box) == pytest.approx(true_shooting_pct(box))


def test_basketball_sport_unknown_metric_raises():
    from openscout.plugins import UnknownMetricError

    sport = BasketballSport()
    with pytest.raises(UnknownMetricError):
        sport.compute("not_a_real_metric", {"pts": 1, "fga": 1, "fta": 1})
