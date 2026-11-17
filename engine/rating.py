"""Build rating, 1 to 10, against a reference set of builds.

1  = unplayable          5  = solid, typical of a good build
3  = weak                8  = top tier
                         10 = broken: far beyond the reference set

Three sub-scores, each placed on a log scale against the reference builds' spread:
  damage    single-target DPS vs a pinnacle boss (bossing setup)
  clear     mapping clear score (damage x area/projectiles)
  toughness effective HP
Overall = 50% damage + 30% clear + 20% toughness.

The reference set (data/rating_calibration.json) is the endgame build of every ascendancy
from tools/sweep.py, built by this engine with the same PoB settings, so the comparison is
like for like. Rate the Uber Endgame stage: that's the build's ceiling.
Planned: add the strongest builds the generator finds and poe.ninja's top ladder builds
(re-run through this engine) as the top anchors.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

CALIBRATION = Path(__file__).parent / "data" / "rating_calibration.json"
WEIGHTS = {"damage": 0.5, "clear": 0.3, "toughness": 0.2}
LABELS = [(9, "Broken"), (7.5, "Top tier"), (6, "Strong"), (4.5, "Solid"), (3, "Weak"), (0, "Unplayable")]


def _percentile(sorted_vals: list[float], q: float) -> float:
    if not sorted_vals:
        return 0.0
    i = (len(sorted_vals) - 1) * q
    lo, hi = math.floor(i), math.ceil(i)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (i - lo)


def anchors(values: list[float]) -> list[tuple[float, float]]:
    """(log10 value, score) points from a reference distribution."""
    v = sorted(x for x in values if x > 0)
    if len(v) < 3:
        raise ValueError("Need at least 3 reference builds to calibrate")
    pts = [(v[0] / 10, 1.0), (_percentile(v, 0.25), 3.5), (_percentile(v, 0.5), 5.0),
           (_percentile(v, 0.75), 6.5), (v[-1], 8.5), (v[-1] * 3, 10.0)]
    return [(math.log10(max(x, 1e-9)), s) for x, s in pts]


def place(value: float, pts: list[tuple[float, float]]) -> float:
    if not value or value <= 0:   # missing (PoB gave no number) or zero
        return 1.0
    lv = math.log10(value)
    if lv <= pts[0][0]:
        return 1.0
    for (x0, s0), (x1, s1) in zip(pts, pts[1:]):
        if lv <= x1:
            return s0 + (s1 - s0) * (lv - x0) / max(x1 - x0, 1e-9)
    return 10.0


def load_calibration() -> dict | None:
    try:
        data = json.loads(CALIBRATION.read_text())
    except (OSError, ValueError):
        return None
    return {k: anchors(v) for k, v in data["metrics"].items()}


def rate(damage: float, clear: float, toughness: float, calibration: dict | None = None) -> dict | None:
    cal = calibration or load_calibration()
    if not cal:
        return None
    subs = {"damage": place(damage, cal["damage"]), "clear": place(clear, cal["clear"]),
            "toughness": place(toughness, cal["toughness"])}
    overall = sum(subs[k] * w for k, w in WEIGHTS.items())
    label = next(name for floor, name in LABELS if overall >= floor)
    return {"overall": round(overall, 1), "label": label, **{k: round(v, 1) for k, v in subs.items()}}
