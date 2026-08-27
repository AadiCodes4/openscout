"""Soccer metrics plugin for openscout.

Implements three metrics:

* **Expected Goals** (``xg``) -- a hand-tuned, logistic-regression-*shaped*
  toy model that scores a shot from its distance, angle, body part, and
  situation. **This is explicitly a simplified educational model, not a
  real calibrated xG model.** Real xG models used by analytics providers
  (Opta, StatsBomb, etc.) are fit on tens of thousands of historical shots
  with dozens of features (defender positions, goalkeeper position, shot
  speed, etc.). The weights here were chosen by hand to produce
  directionally sensible, monotonic output (closer + more central + a shot
  with the foot => higher xG) -- nothing more.
* **Pass completion %%** (``pass_pct``) -- straightforward completed/attempted.
* **Zone threat added** (``xt_added``) -- a simplified, *un-calibrated*
  "expected threat"-style metric: the pitch is divided into a 12x8 grid,
  each zone is assigned a smooth, deterministic "attacking value" based on
  its distance from the opponent's goal and how central it is, and a pass
  or carry's contribution is the value of the zone it ends in minus the
  value of the zone it started in. This is inspired by the general idea
  behind possession-value / expected-threat (xT) models (e.g. Karun Singh's
  public write-up) but is **not** a trained/calibrated model of any kind --
  it's a fixed formula.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from ..plugins import SportBase, UnknownMetricError

Shot = Mapping[str, Any]
Pass = Mapping[str, Any]

# --- pitch / grid geometry -------------------------------------------------
# Pitch coordinates are normalized to 0-100 on both axes:
#   x: 0 = own goal line, 100 = opponent's goal line
#   y: 0 = one touchline, 100 = the other
GRID_COLS = 12
GRID_ROWS = 8
GOAL_X = 100.0
GOAL_Y = 50.0
_MAX_DIST = math.hypot(GOAL_X, GOAL_Y)  # distance from own corner to opp. goal


# --- Expected Goals (toy model) --------------------------------------------

# Hand-tuned logistic weights. See module docstring: this is a toy model,
# not a calibrated one. Coefficients are on (distance in metres, angle in
# degrees) plus categorical adjustments.
_XG_INTERCEPT = -0.30
_XG_W_DISTANCE = -0.11   # farther away -> lower xG
_XG_W_ANGLE = 0.020      # wider shooting angle -> higher xG
_XG_HEADER_PENALTY = -0.45
#: Note: "penalty" is deliberately absent -- it's handled as a fixed value
#: (see _PENALTY_XG below) before this table is ever consulted.
_XG_SITUATION_ADJUST: dict[str, float] = {
    "open_play": 0.0,
    "set_piece": -0.20,
    "counter": 0.15,
}
_PENALTY_XG = 0.79  # widely-cited rough real-world penalty conversion rate

_VALID_BODY_PARTS = {"foot", "head", "other"}
_VALID_SITUATIONS = {"open_play", "set_piece", "counter", "penalty"}


def _sigmoid(z: float) -> float:
    return 1.0 / (1.0 + math.exp(-z))


def expected_goals(shot: Shot) -> float:
    """Compute a toy xG value for a single shot dict.

    Required keys: ``distance`` (metres from goal), ``angle`` (degrees of
    goalmouth subtended, 0-180, wider = more open). Optional keys:
    ``body_part`` (one of "foot"/"head"/"other", default "foot") and
    ``situation`` (one of "open_play"/"set_piece"/"counter"/"penalty",
    default "open_play").
    """
    situation = shot.get("situation", "open_play")
    if situation not in _VALID_SITUATIONS:
        raise ValueError(
            f"unknown situation {situation!r}; expected one of {sorted(_VALID_SITUATIONS)}"
        )
    if situation == "penalty":
        return _PENALTY_XG

    if "distance" not in shot or "angle" not in shot:
        raise ValueError("shot dict requires 'distance' and 'angle' fields")

    distance = float(shot["distance"])
    angle = float(shot["angle"])
    body_part = shot.get("body_part", "foot")
    if body_part not in _VALID_BODY_PARTS:
        raise ValueError(
            f"unknown body_part {body_part!r}; expected one of {sorted(_VALID_BODY_PARTS)}"
        )

    z = _XG_INTERCEPT + _XG_W_DISTANCE * distance + _XG_W_ANGLE * angle
    if body_part == "head":
        z += _XG_HEADER_PENALTY
    z += _XG_SITUATION_ADJUST[situation]

    return _sigmoid(z)


def expected_goals_many(shots: list[Shot]) -> dict[str, Any]:
    """Compute per-shot xG plus the summed total for a list of shots."""
    values = [expected_goals(shot) for shot in shots]
    return {"total_xg": sum(values), "shot_xg": values}


# --- Pass completion --------------------------------------------------------

def pass_completion_pct(passes: list[Pass]) -> float:
    """Percentage of passes with a truthy ``completed`` field, in [0, 100]."""
    if not passes:
        return 0.0
    completed = sum(1 for p in passes if p.get("completed"))
    return 100.0 * completed / len(passes)


# --- Zone threat (xT-lite) ---------------------------------------------------

def zone_value(x: float, y: float) -> float:
    """Deterministic "attacking value" of pitch coordinate (x, y).

    Value increases smoothly the closer and more central a location is to
    the opponent's goal at (100, 50). This is a fixed formula, not a
    trained model -- see module docstring.
    """
    distance = math.hypot(GOAL_X - x, GOAL_Y - y)
    return math.exp(-distance / (_MAX_DIST / 3))


def zone_of(x: float, y: float) -> tuple[int, int]:
    """Map a continuous pitch coordinate to its (col, row) grid cell."""
    col = min(GRID_COLS - 1, max(0, int(x / 100 * GRID_COLS)))
    row = min(GRID_ROWS - 1, max(0, int(y / 100 * GRID_ROWS)))
    return col, row


def _zone_center(col: int, row: int) -> tuple[float, float]:
    x = (col + 0.5) * (100 / GRID_COLS)
    y = (row + 0.5) * (100 / GRID_ROWS)
    return x, y


def action_threat(action: Mapping[str, float]) -> float:
    """Threat added by one pass/carry: value(end zone) - value(start zone).

    ``action`` must contain ``start_x, start_y, end_x, end_y`` in the 0-100
    normalized pitch coordinate system described in the module docstring.
    """
    start_col, start_row = zone_of(action["start_x"], action["start_y"])
    end_col, end_row = zone_of(action["end_x"], action["end_y"])
    start_value = zone_value(*_zone_center(start_col, start_row))
    end_value = zone_value(*_zone_center(end_col, end_row))
    return end_value - start_value


def total_threat_added(actions: list[Mapping[str, float]]) -> dict[str, Any]:
    """Sum (and list) the threat added by a sequence of passes/carries."""
    per_action = [action_threat(a) for a in actions]
    return {"total_xt": sum(per_action), "action_xt": per_action}


class SoccerSport(SportBase):
    """The built-in soccer sport plugin."""

    name = "soccer"

    def list_metrics(self) -> list[str]:
        return ["xg", "pass_pct", "xt_added"]

    def compute(self, metric_name: str, data: Any) -> Any:
        if metric_name == "xg":
            if isinstance(data, Mapping):
                return expected_goals(data)
            return expected_goals_many(list(data))
        if metric_name == "pass_pct":
            return pass_completion_pct(list(data))
        if metric_name == "xt_added":
            if isinstance(data, Mapping):
                return action_threat(data)
            return total_threat_added(list(data))
        raise UnknownMetricError(
            f"soccer plugin has no metric {metric_name!r}. "
            f"Available metrics: {', '.join(self.list_metrics())}"
        )
