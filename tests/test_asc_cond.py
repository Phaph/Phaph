"""tools/asc_cond.py: the sums, without PoB."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine" / "tools"))
import asc_cond  # noqa: E402


def test_interaction():
    assert abs(asc_cond.interaction(100, 120, 130, 156)) < 1e-9        # 1.2 x 1.3: they only multiply
    assert abs(asc_cond.interaction(100, 100, 100, 125) - 0.25) < 1e-9  # only together
    assert asc_cond.interaction(100, 0, 100, 50) == 0.0


def test_conditions_are_checkboxes():
    text = '{ var = "conditionEnemyFrozen", type = "check" } { var = "conditionStacks", type = "count" } { var = "useX", type = "check" }'
    assert asc_cond.all_conditions(text) == ["conditionEnemyFrozen"]


def test_specific_takes_out_the_usual():
    row = lambda v: {"error": None, "dps": 100_000, "inter": [["Crushing", "EnemyHeavyStunned", v, v]]}
    scans = {"Titan": {"skills": {**{f"S{i}": row(0.25) for i in range(5)}, "Odd": row(0.75)}}}
    rows = asc_cond.specific(scans)
    assert rows[0][:2] == (0.5, "Odd") and all(abs(r[0]) < 1e-9 for r in rows[1:])


def test_a_cancelled_penalty_is_no_find():
    # Pathfinder Rapid Shot: notable alone +4.4%, Frozen alone x0.2, both +4.4%: reads +390%, pays nothing
    assert not asc_cond.pays(0.044, 3.9, 0.044)
    assert asc_cond.pays(0.0, 0.25, 0.25)        # Titan: 25% more vs Heavy Stunned, only together
    assert not asc_cond.pays(0.30, 0.02, 0.326)  # notable alone carries it
    row = {"error": None, "dps": 100_000, "plain": {"Relentless": 0.044}, "inter": [["Relentless", "Frozen", 3.9, 0.044]]}
    assert asc_cond.specific({"Pathfinder": {"skills": {"Rapid Shot": row}}}) == []
