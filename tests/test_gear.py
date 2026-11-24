"""Gear crafting and the seven stages."""
import re

import pytest

from gear import CAMPAIGN, SCORE_FIELDS, STAGE_DEFS, _value_at, craft_gear, make_stage


def test_value_at():
    assert _value_at("+(50-70) to maximum Life", 0.5) == "+60 to maximum Life"
    assert _value_at("Adds (10-20) to (30-40) Fire Damage", 1.0) == "Adds 20 to 40 Fire Damage"
    assert _value_at("+(1.5-2.5)% to Critical Hit Chance", 0.0) == "+1.5% to Critical Hit Chance"


def test_seven_stages_in_order():
    assert list(STAGE_DEFS) == ["act1", "act2", "act34", "interludes", "early", "mid", "end"]
    assert [make_stage(k).name for k in STAGE_DEFS] == ["Act 1", "Act 2", "Acts 3\u20134", "Interludes", "Early Endgame",
                                                        "Mid Endgame", "Uber Endgame"]
    stages = [make_stage(k) for k in STAGE_DEFS]
    # Everything a player has only grows: level, item level, affixes, sockets, unique access, ascendancy points.
    for a, b in zip(stages, stages[1:]):
        assert a.level < b.level and a.item_level <= b.item_level and a.max_affixes <= b.max_affixes
        assert a.sockets <= b.sockets and a.ascendancy_points <= b.ascendancy_points and a.roll <= b.roll
    # Support sockets: 2 base, a Lesser Jeweller's Orb (3) in the campaign, a Greater (4) early endgame, a Perfect (5).
    assert [s.sockets for s in stages] == [2, 3, 3, 3, 4, 5, 5]
    assert all(make_stage(k).light and make_stage(k).jewel_affixes == 0 for k in CAMPAIGN)
    assert not any(make_stage(k).light for k in ("early", "mid", "end"))
    assert make_stage("act1").uniques == "common" and make_stage("end").uniques == "all"
    # The acts: a few common uniques the build can use, never a full set of them.
    assert [make_stage(k).max_uniques for k in CAMPAIGN] == [2, 2, 3, 3]
    assert make_stage("end").max_uniques is None
    uber = make_stage("end")
    assert uber.focus == "bossing" and uber.def_mult > 1 and uber.chaos_target > 0 and uber.res_target == 75


def test_unknown_stage_rejected():
    with pytest.raises(ValueError):
        make_stage("leveling")


def test_make_stage_is_a_copy():
    st = make_stage("end")
    st.level = 1
    assert make_stage("end").level == 95


@pytest.fixture(scope="module")
def crafted(pob):
    st = make_stage("early")
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
    st = make_stage("early")
    pob.new()
    pob.set_class("Sorceress", "Stormweaver")
    pob.set_level(st.level)
    pob.add_skill(["Spark"])
    craft_gear(pob, st, "Wand", None, mode="mapping", log=lambda *a: None)
    stats = pob.calc(SCORE_FIELDS)
    for k in ("FireResist", "ColdResist", "LightningResist"):
        assert stats[k] >= 75, k


def test_unknown_uniques_only_for_pinnacle_bosses(monkeypatch):
    """Regression: Mageblood was suggested for a mid-game build because poe.ninja had no data on it."""
    import gear
    from gear import _unique_allowed
    monkeypatch.setattr(gear, "_PRICES", {})
    assert _unique_allowed("Mageblood, Utility Belt", make_stage("mid")) is False
    assert _unique_allowed("Mageblood, Utility Belt", make_stage("end")) is True


def test_unique_access_grows_with_the_stage(monkeypatch):
    import gear
    from gear import _unique_allowed
    monkeypatch.setattr(gear, "_PRICES", {"Mageblood": 112, "Headhunter": 8.5, "Bramblejack": 0.05})
    allowed = {k: [n for n in ("Mageblood", "Headhunter", "Bramblejack") if _unique_allowed(n, make_stage(k))]
               for k in STAGE_DEFS}
    for k in ("act1", "act2", "act34", "interludes", "early"):
        assert allowed[k] == ["Bramblejack"], k                                 # common uniques drop from Act 1 on
    assert allowed["mid"] == ["Headhunter", "Bramblejack"]
    assert allowed["end"] == ["Mageblood", "Headhunter", "Bramblejack"]         # best in slot


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
    # Uber Endgame: one tier below best by default, the best tier offered for the item's few top-tier slots.
    opt = _tier_choices(affixes, make_stage("end"))["Life"]
    assert (opt["level"], opt["_tier"], opt["_tiers"]) == (30, 2, 4)
    assert (opt["_best"]["level"], opt["_best"]["_tier"], opt["_best"]["_is_top"]) == (60, 1, True)
    assert make_stage("end").top_mods == 4 and make_stage("mid").top_mods == 2
    assert make_stage("act1").top_mods == 0   # self-found: no top-tier mods


def test_top_tier_slots_are_capped(pob, monk):
    """A Mid Endgame item may hold at most 2 best-tier mods; the crafter spends them on what matters most."""
    from gear import craft_gear
    stage = make_stage("mid")
    for p in craft_gear(pob, stage, "Staff", "Warstaff", log=lambda *a: None):
        if not p.unique:
            assert sum(1 for i in p.affix_info if i.get("tier") == 1 and (i.get("of") or 0) > 1) <= stage.top_mods, p
            assert len(p.affixes) <= stage.max_affixes


class _FakePob:
    """Just enough of a build: each slot's item adds a fixed amount of damage."""
    def __init__(self, worth):
        self.worth, self.worn = worth, {}

    def calc(self, fields=None):
        dps = 1000 + sum(self.worth.get(raw, 500) for raw in self.worn.values())
        return {"TotalDPS": dps, "CombinedDPS": dps, "TotalEHP": 1000, "FireResist": 75, "ColdResist": 75,
                "LightningResist": 75, "ChaosResist": 75, "Str": 100, "Dex": 100, "Int": 100}

    def send(self, cmd, **kw):
        assert cmd == "equip"
        self.worn[kw["slot"]] = kw["raw"]
        return {"output": self.calc()}


def test_uniques_are_checked_again_once_the_rest_is_set():
    """A unique that no longer beats its rare goes back; one that still does, and the anchor, stay as they were."""
    from gear import Scorer, _revisit_uniques, _Work
    pob = _FakePob({"BAD": 0, "GOOD": 5000, "ANCHOR": 0})
    works = [_Work("Helmet", "Cap", "h", {}, unique="Bad", unique_raw="BAD"),
             _Work("Gloves", "Mitts", "g", {}, unique="Good", unique_raw="GOOD"),
             _Work("Boots", "Shoes", "b", {}, unique="Anchor", unique_raw="ANCHOR"),
             _Work("Belt", "Belt", "r", {}, lines=["+10 to Strength"], picked=["x"])]
    for w in works:
        pob.send("equip", slot=w.slot, raw=w.raw())
    belt = works[3].raw()
    n = _revisit_uniques(pob, works, make_stage("end"), Scorer(metric="total"), skip=works[2], log=lambda *a: None)
    assert n == 1 and [w.unique for w in works] == [None, "Good", "Anchor", None]
    assert pob.worn["Helmet"] == works[0].raw() != "BAD"
    assert (pob.worn["Gloves"], pob.worn["Boots"], pob.worn["Belt"]) == ("GOOD", "ANCHOR", belt)
