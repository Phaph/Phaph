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


def test_unpriced_uniques_only_on_no_limit(monkeypatch):
    """Regression: Mageblood was suggested for a 5-30 divine build because it had no price."""
    import gear
    from gear import _unique_allowed
    monkeypatch.setattr(gear, "_PRICES", {})
    assert _unique_allowed("Mageblood, Utility Belt", make_stage("end", "medium"))[0] is False
    assert _unique_allowed("Mageblood, Utility Belt", make_stage("end", "high"))[0] is False
    assert _unique_allowed("Mageblood, Utility Belt", make_stage("end", "unlimited")) == (True, "price unknown")


def test_priced_uniques_follow_budget(monkeypatch):
    import gear
    from gear import _unique_allowed
    monkeypatch.setattr(gear, "_PRICES", {"Mageblood": 112, "Headhunter": 8.5})
    assert _unique_allowed("Mageblood, Utility Belt", make_stage("end", "high")) == (False, "~112 div")
    assert _unique_allowed("Mageblood, Utility Belt", make_stage("end", "unlimited")) == (True, "~112 div")
    assert _unique_allowed("Headhunter, Heavy Belt", make_stage("end", "medium")) == (True, "~8.5 div")
    assert _unique_allowed("Headhunter, Heavy Belt", make_stage("end", "budget"))[0] is False


def test_price_picker_skips_fixed_and_corrupted_listings():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine" / "tools"))
    from fetch_prices import pick_prices
    lines = [
        {"name": "Winter's Bite", "baseType": "Glass Shank", "primaryValue": 45185000, "listingCount": 1},
        {"name": "Voices", "baseType": "Sapphire", "primaryValue": 1329, "listingCount": 70, "corrupted": True},
        {"name": "Runeseeker's Call", "baseType": "Runic Fork", "primaryValue": 6455, "listingCount": 69},
        {"name": "Runeseeker's Call", "baseType": "Runemastered Runic Fork", "primaryValue": 1620, "listingCount": 34},
        {"name": "Temporalis", "baseType": "Runemastered Silk Robe", "primaryValue": 6876, "listingCount": 7},
        {"name": "Widowhail", "baseType": "Crude Bow", "primaryValue": 0.00156, "listingCount": 3531},
    ]
    assert pick_prices(lines) == {"Runeseeker's Call": 6455, "Temporalis": 6876, "Widowhail": 0.002}


def test_tier_choices_record_tier():
    from gear import _tier_choices
    affixes = [{"group": "Life", "level": lvl, "type": "Prefix"} for lvl in (1, 10, 30, 60)]
    # No limit: one tier below best by default, the best tier offered for the item's few top-tier slots.
    opt = _tier_choices(affixes, make_stage("end", "unlimited"))["Life"]
    assert (opt["level"], opt["_tier"], opt["_tiers"]) == (30, 2, 4)
    assert (opt["_best"]["level"], opt["_best"]["_tier"], opt["_best"]["_is_top"]) == (60, 1, True)
    assert make_stage("end", "unlimited").top_mods == 4 and make_stage("end", "high").top_mods == 2
    cheap = _tier_choices(affixes, make_stage("end", "free"))["Life"]
    assert cheap["_tier"] == 1 + make_stage("end", "free").tier_drop and make_stage("end", "free").top_mods == 0


def test_top_tier_slots_are_capped(pob, monk):
    """A High budget item may hold at most 2 best-tier mods; the crafter spends them on what matters most."""
    from gear import craft_gear
    stage = make_stage("end", "high")
    for p in craft_gear(pob, stage, "Staff", "Warstaff", log=lambda *a: None):
        if not p.unique:
            assert sum(1 for i in p.affix_info if i.get("tier") == 1 and (i.get("of") or 0) > 1) <= stage.top_mods, p
            assert len(p.affixes) <= stage.max_affixes
