"""Every crafted item must be one the game could actually make (gear.item_problems)."""
import pytest

import gear
from gear import _Work, base_implicits, craft_gear, item_problems, make_stage


def affix(group, kind, adds=(), wk=("default",), wv=(1,), stats=None, level=1):
    return {"group": group, "type": kind, "adds": list(adds), "wk": list(wk), "wv": list(wv), "stats": list(stats or ()),
            "level": level, "lines": [group]}


def work(*affixes, tags=("wand", "default")):
    w = _Work("Weapon 1", "Test Wand", "t", {}, base_tags=frozenset(tags))
    for i, a in enumerate(affixes):
        a["stats"] = a["stats"] or [1000 + i]   # its own stat unless the test says otherwise
        w.meta.append((a["group"], a, a["lines"]))
        w.picked.append(a["group"])
    return w


COLD = dict(adds=("no_fire_spell_mods", "no_lightning_spell_mods", "no_chaos_spell_mods", "no_physical_spell_mods"),
            wk=("no_cold_spell_mods", "wand", "default"), wv=(0, 1, 0))
PHYS = dict(adds=("no_fire_spell_mods", "no_cold_spell_mods", "no_lightning_spell_mods", "no_chaos_spell_mods"),
            wk=("no_physical_spell_mods", "wand", "default"), wv=(0, 1, 0))


def test_rule_cold_and_physical_spell_levels_exclude_each_other():
    bad = work(affix("ColdLevels", "Suffix", **COLD, stats=(961,)), affix("PhysLevels", "Suffix", **PHYS, stats=(1476,)))
    assert item_problems(bad)
    ok = work(affix("ColdLevels", "Suffix", **COLD, stats=(961,)), affix("AllSpellLevels", "Suffix", stats=(950,)))
    assert item_problems(ok) == []


def test_rule_three_prefixes_three_suffixes_one_per_group_one_per_stat():
    assert item_problems(work(*[affix(f"S{i}", "Suffix") for i in range(4)]))
    assert item_problems(work(affix("A", "Prefix"), affix("A", "Prefix")))
    assert item_problems(work(affix("A", "Prefix", stats=(5,)), affix("B", "Prefix", stats=(5,))))
    assert item_problems(work(affix("A", "Prefix", level=81)), item_level=75)
    assert item_problems(work(*[affix(f"P{i}", "Prefix") for i in range(3)], *[affix(f"S{i}", "Suffix") for i in range(3)])) == []


def test_restricted_bases_are_never_used():
    absent = {"implicit": "-1 Prefix Modifier allowed\n-1 Suffix Modifier allowed\n{variant:1}Grants Skill: Level (1-20) Archmage"}
    assert base_implicits(absent, 0.5) is None
    assert base_implicits({"implicit": "+(7-10)% to all Elemental Resistances"}, 1.0) == ["+10% to all Elemental Resistances"]


def test_genesis_only_mods_are_not_offered(pob):
    belt = pob.send("affixes", base="Utility Belt", max_level=100)
    assert not any("Level of all Minion Skills" in a["lines"][0] for a in belt["affixes"]), "Genesis-tree-only mod offered"
    assert not any(t.startswith("genesis") for t in belt["item_tags"])


def _skill_for(catalog, weapon, attack=True):
    for s in catalog:
        types = set(s["types"])
        if weapon in s.get("weapons", []) and ("Attack" in types) == attack and not types & {"Buff", "Meta", "Triggered", "Persistent"}:
            return s["name"]
    return None


# (class, weapon type, weapon subtype, offhand, attack skill?)
BUILDS = [
    ("Sorceress", "Wand", None, None, False),
    ("Sorceress", "Staff", "none", None, False),
    ("Monk", "Staff", "Warstaff", None, True),
    ("Ranger", "Bow", None, None, True),
    ("Mercenary", "Crossbow", None, None, True),
    ("Witch", "Sceptre", None, None, False),
    ("Huntress", "Spear", None, "Shield", True),
    ("Warrior", "Two Hand Mace", None, None, True),
    ("Warrior", "One Hand Mace", None, "Shield", True),
]
STAGES = ["act1", "early", "end"]


@pytest.mark.parametrize("cls,wtype,wsub,off,attack", BUILDS, ids=[f"{b[0]}-{b[1]}" for b in BUILDS])
def test_every_crafted_item_is_legal(pob, monkeypatch, cls, wtype, wsub, off, attack):
    monkeypatch.setattr(gear, "STRICT_ITEMS", True)
    catalog = pob.send("skill_catalog")["skills"]
    skill = _skill_for(catalog, wtype, attack) or _skill_for(catalog, wtype, not attack) or ("Spark" if not attack else None)
    assert skill, f"no skill found for {wtype}"
    for key in STAGES:
        stage = make_stage(key)
        pob.new()
        pob.set_class(cls)
        pob.set_level(stage.level)
        pob.add_skill([skill])
        plans = craft_gear(pob, stage, wtype, wsub, offhand_type=off, log=lambda *a: None)   # raises on any broken rule
        assert plans
        for p in plans:
            assert p.unique or len(p.affixes) <= 6


def test_special_and_unlisted_bases_are_never_used(monkeypatch):
    import gear
    assert not gear.base_usable({"name": "Golden Mantle", "tags": ["armour", "demigods", "not_for_sale"], "implicit": ""})
    monkeypatch.setattr(gear, "_AVAILABILITY", {"Dark Staff": 0, "Wyrm Quarterstaff": 2106})
    assert not gear.base_usable({"name": "Dark Staff", "tags": ["staff"], "implicit": ""})
    assert gear.base_usable({"name": "Wyrm Quarterstaff", "tags": ["staff"], "implicit": ""})
    assert gear.base_usable({"name": "Not Yet Checked", "tags": ["staff"], "implicit": ""})


def test_bows_get_a_quiver_and_wands_a_focus(pob):
    """Empty until 2026-11-24: nothing filled Weapon 2 unless a skill or an anchor asked for it."""
    for cls, wtype, skill, off in (("Ranger", "Bow", "Lightning Arrow", "quiver"), ("Witch", "Wand", "Spark", "focus"),
                                   ("Witch", "Staff", "Spark", None)):
        stage = make_stage("end")
        pob.new()
        pob.set_class(cls)
        pob.set_level(stage.level)
        pob.add_skill([skill])
        plans = craft_gear(pob, stage, wtype, "none" if wtype == "Staff" else None, uniques=False, log=lambda *a: None)
        held = [p for p in plans if p.slot == "Weapon 2"]
        assert bool(held) == bool(off), wtype
        if off:
            assert off in held[0].base.lower()
            assert pob.calc(["TotalDPS"])["TotalDPS"] > 0


def test_one_handed_martial_weapons_fill_the_off_hand(pob):
    """A second weapon or a shield, whichever scores better; a spear can only take a shield."""
    for cls, wtype, skill, kinds in (("Warrior", "One Hand Mace", "Boneshatter", {"One Hand Mace", "Shield"}),
                                     ("Huntress", "Spear", "Whirlwind Lance", {"Shield"})):
        stage = make_stage("end")
        pob.new()
        pob.set_class(cls)
        pob.set_level(stage.level)
        pob.add_skill([skill])
        types = {b["name"]: b["type"] for b in pob.send("bases", max_level=stage.item_level)["bases"]}
        held = [p for p in craft_gear(pob, stage, wtype, uniques=False, log=lambda *a: None) if p.slot == "Weapon 2"]
        assert len(held) == 1 and types[held[0].base] in kinds
