"""Basketball metrics plugin for openscout.

Implements a handful of well-established basketball box-score metrics:

* **True Shooting %** (``ts_pct``) -- shooting efficiency that accounts for
  the extra value of three-pointers and the existence of free throws.
* **Effective Field Goal %** (``efg_pct``) -- field goal percentage adjusted
  so a made three is worth the extra half-point of value it provides.
* **Four Factors** (``four_factors``) -- Dean Oliver's four team-level
  factors: eFG%, turnover rate, offensive rebound rate, and free throw rate.
* **Game-Score-style composite** (``per_lite``) -- a simplified, single-game
  productivity composite *inspired by* John Hollinger's "Game Score" box
  score formula. This is explicitly **not** the real, league-and-pace
  adjusted Player Efficiency Rating (PER); it is a lightweight, dependency-free
  stand-in that is fun to compute from a single box score and clearly labeled
  as such.

Box score input format
-----------------------
Every metric accepts either a single box score ``dict`` or a ``list`` of
box score ``dict``s (which are summed field-by-field before computing --
handy for turning several games into one aggregate). Recognized fields
(all optional unless the metric requires them):

``pts, fg, fga, fg3, fg3a, ft, fta, orb, drb, ast, stl, blk, tov, pf, min``
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..plugins import SportBase, UnknownMetricError

BoxScore = Mapping[str, float]
BoxScoreInput = BoxScore | list[BoxScore]

_NUMERIC_FIELDS = (
    "pts", "fg", "fga", "fg3", "fg3a", "ft", "fta",
    "orb", "drb", "ast", "stl", "blk", "tov", "pf", "min", "opp_drb",
)


def _aggregate(data: BoxScoreInput) -> dict[str, float]:
    """Sum a single box score dict or a list of them into one dict of totals."""
    if isinstance(data, Mapping):
        rows: list[BoxScore] = [data]
    else:
        rows = list(data)
        if not rows:
            raise ValueError("box score data must contain at least one entry")

    # Only fields actually present in at least one row end up in the totals
    # dict at all -- this lets metrics that require a specific field (e.g.
    # opp_drb for ORB%) tell "field genuinely absent" apart from "field
    # present but happened to sum to zero".
    totals: dict[str, float] = {}
    for row in rows:
        for field in _NUMERIC_FIELDS:
            if field in row and row[field] is not None:
                totals[field] = totals.get(field, 0.0) + float(row[field])
    return totals


def _get(totals: Mapping[str, float], field: str) -> float:
    return totals.get(field, 0.0)


def _require(totals: Mapping[str, float], *fields: str) -> None:
    missing = [f for f in fields if f not in totals]
    if missing:
        raise ValueError(f"box score is missing required field(s): {', '.join(missing)}")


def true_shooting_pct(data: BoxScoreInput) -> float:
    """True Shooting %% = PTS / (2 * (FGA + 0.44 * FTA)).

    Returns 0.0 for a box score with zero shooting attempts rather than
    raising a division-by-zero error, since "no shots taken" is a valid
    (if rare) real-world box score.
    """
    totals = _aggregate(data)
    pts, fga, fta = _get(totals, "pts"), _get(totals, "fga"), _get(totals, "fta")
    denominator = 2 * (fga + 0.44 * fta)
    if denominator == 0:
        return 0.0
    return pts / denominator


def effective_fg_pct(data: BoxScoreInput) -> float:
    """Effective Field Goal %% = (FG + 0.5 * FG3) / FGA."""
    totals = _aggregate(data)
    fg, fg3, fga = _get(totals, "fg"), _get(totals, "fg3"), _get(totals, "fga")
    if fga == 0:
        return 0.0
    return (fg + 0.5 * fg3) / fga


def four_factors(data: BoxScoreInput) -> dict[str, float]:
    """Dean Oliver's "Four Factors" of basketball success.

    * ``efg_pct``  = (FG + 0.5*FG3) / FGA
    * ``tov_pct``  = TOV / (FGA + 0.44*FTA + TOV)
    * ``orb_pct``  = ORB / (ORB + opponent DRB)   -- requires ``opp_drb``
    * ``ft_rate``  = FTA / FGA

    ``orb_pct`` requires the opponent's defensive rebounds (``opp_drb``) in
    the input, since offensive rebound rate is inherently a two-team stat
    (it's your offensive boards vs. the boards the other team denied you).
    """
    totals = _aggregate(data)
    _require(totals, "opp_drb")

    fga, fta, tov = _get(totals, "fga"), _get(totals, "fta"), _get(totals, "tov")
    orb, opp_drb = _get(totals, "orb"), _get(totals, "opp_drb")

    poss_denominator = fga + 0.44 * fta + tov
    tov_pct = tov / poss_denominator if poss_denominator else 0.0

    orb_denominator = orb + opp_drb
    orb_pct = orb / orb_denominator if orb_denominator else 0.0

    ft_rate = fta / fga if fga else 0.0

    return {
        "efg_pct": effective_fg_pct(totals),
        "tov_pct": tov_pct,
        "orb_pct": orb_pct,
        "ft_rate": ft_rate,
    }


def per_lite(data: BoxScoreInput) -> float:
    """A simplified single-game productivity composite.

    This is **inspired by** John Hollinger's publicly documented "Game
    Score" formula and is explicitly a stand-in / toy metric -- it is
    *not* the real Player Efficiency Rating (PER), which additionally
    normalizes for pace, minutes, and league averages. We call it
    "PER-lite" purely because it is a single-number, higher-is-better
    productivity composite in that spirit.

    Formula::

        per_lite = PTS + 0.4*FG - 0.7*FGA - 0.4*(FTA - FT)
                   + 0.7*ORB + 0.3*DRB + STL + 0.7*AST + 0.7*BLK
                   - 0.4*PF - TOV
    """
    t = _aggregate(data)
    return (
        _get(t, "pts")
        + 0.4 * _get(t, "fg")
        - 0.7 * _get(t, "fga")
        - 0.4 * (_get(t, "fta") - _get(t, "ft"))
        + 0.7 * _get(t, "orb")
        + 0.3 * _get(t, "drb")
        + _get(t, "stl")
        + 0.7 * _get(t, "ast")
        + 0.7 * _get(t, "blk")
        - 0.4 * _get(t, "pf")
        - _get(t, "tov")
    )


class BasketballSport(SportBase):
    """The built-in basketball sport plugin."""

    name = "basketball"

    _METRICS = {
        "ts_pct": true_shooting_pct,
        "efg_pct": effective_fg_pct,
        "four_factors": four_factors,
        "per_lite": per_lite,
    }

    def list_metrics(self) -> list[str]:
        return sorted(self._METRICS)

    def compute(self, metric_name: str, data: Any) -> Any:
        try:
            fn = self._METRICS[metric_name]
        except KeyError as exc:
            raise UnknownMetricError(
                f"basketball plugin has no metric {metric_name!r}. "
                f"Available metrics: {', '.join(self.list_metrics())}"
            ) from exc
        return fn(data)
