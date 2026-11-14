"""Gear crafting and budget rules."""
import re

import pytest

from gear import BUDGET_ORDER, SCORE_FIELDS, _value_at, craft_gear, make_stage


def test_value_at():
    assert _value_at("+(50-70) to maximum Life", 0.5) == "+60 to maximum Life"
    assert _value_at("Adds (10-20) to (30-40) Fire Damage", 1.0) == "Adds 20 to 40 Fire Damage"
    assert _value_at("+(1.5-2.5)% to Critical Hit Chance", 0.0) == "+1.5% to Critical Hit Chance"


def test_budget_caps_every_stage():
    for budget in BUDGET_ORDER:
        cap = BUDGET_ORDER.index(budget)
        for key in ("leveling", "early", "mid", "end"):
            st = make_stage(key, budget)
            assert st.max_affixes <= make_stage(key, "unlimited").max_affixes
            # The label is the budget actually used, never above the cap.
            used = next(b for b in BUDGET_ORDER if make_stage("end", b).budget == st.budget)
            assert BUDGET_ORDER.index(used) <= cap


def test_unknown_budget_rejected():
    with pytest.raises(ValueError):
        make_stage("end", "mirror")


@pytest.fixture(scope="module")
def crafted(pob):
    st = make_stage("early", "budget")
    pob.new()
    pob.set_class("Monk", "Invoker")
    pob.set_level(st.level)
    pob.add_skill(["Tempest Flurry"])
    plans = craft_gear(pob, st, "Staff", "Warstaff", log=lambda *a: None)
    return st, plans, pob.calc(SCORE_FIELDS)


def test_every_slot_crafted(crafted):
    _, plans, _ = crafted
    slots = {p.slot for p in plans}
    assert {"Weapon 1", "Helmet", "Body Armour", "Gloves", "Boots", "Amulet", "Ring 1", "Ring 2", "Belt"} <= slots


def test_affix_limits(crafted):
    st, plans, _ = crafted
    for p in plans:
        assert len(p.affixes) <= st.max_affixes, p.slot


def test_resistances_capped_at_early_maps(crafted):
    _, _, stats = crafted
    for k in ("FireResist", "ColdResist", "LightningResist"):
        assert stats[k] >= 75, k


def test_no_wasted_triple_resist_items(crafted):
    """Regression: every armour piece used to roll all three resistances."""
    _, plans, _ = crafted
    triple = [p.slot for p in plans
              if sum(bool(re.search(f"to {e} Resistance", " ".join(p.affixes))) for e in ("Fire", "Cold", "Lightning")) == 3]
    assert len(triple) <= 1, triple


def test_caster_caps_resistances_when_items_are_full(pob):
    """Regression: with every affix slot used, resistances stopped short (e.g. 73% or 45%)."""
    st = make_stage("early", "budget")
    pob.new()
    pob.set_class("Sorceress", "Stormweaver")
    pob.set_level(st.level)
    pob.add_skill(["Spark"])
    craft_gear(pob, st, "Wand", None, mode="mapping", log=lambda *a: None)
    stats = pob.calc(SCORE_FIELDS)
    for k in ("FireResist", "ColdResist", "LightningResist"):
        assert stats[k] >= 75, k
