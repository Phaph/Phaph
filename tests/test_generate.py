"""Build generator: theme filtering, weapon choice, planning and the feedback option,
plus the engine features it relies on (conditions, spirit, weapon set 2)."""
import pytest
from conftest import SPEAR, STAFF

from gear import craft_weapon, make_stage
from generate import main_skills, options, plan_build, weapon_options
from spirit import optimise_spirit


@pytest.fixture(scope="module")
def catalog(pob):
    return pob.send("skill_catalog")["skills"]


def names(skills):
    return {s["name"] for s in skills}


def test_theme_filters(catalog):
    lightning = names(main_skills(catalog, {"damage": ["lightning"]}))
    assert {"Spark", "Arc", "Tempest Flurry"} <= lightning
    assert "Lightning Warp" not in lightning, "teleports are not main skills"
    assert "His Scattering Calamity" not in lightning, "item-granted skills need their item"
    assert "Elemental Weakness" not in lightning, "curses are not main skills"
    minions = names(main_skills(catalog, {"kinds": ["minion"]}))
    assert "Skeletal Storm Mage" in minions and "Spark" not in minions
    bleed = names(main_skills(catalog, {"ailment": "bleed", "kinds": ["melee"]}))
    assert "Rake" in bleed and "Parry" not in bleed


def test_weapon_options(catalog):
    by = {s["name"]: s for s in catalog}
    assert weapon_options(by["Tempest Flurry"], {}) == [("Staff", "Warstaff", None)]
    assert ("Wand", None, None) in weapon_options(by["Spark"], {})
    assert ("Staff", "none", None) in weapon_options(by["Spark"], {}), "spells use caster staves"
    assert all(o[2] == "Shield" for o in weapon_options(by["Shield Wall"], {}))
    assert weapon_options(by["Rake"], {"weapons": ["Bow"]}) == []


def _row(skill, asc, score, dps, weapon="Staff"):
    return {"skill": skill, "ascendancy": asc, "cls": "Monk", "weapon_type": weapon, "weapon_subtype": None,
            "offhand_type": None, "score": score, "dps": dps}


RESULT = {"request": {"budget": "medium"}, "ranked": [
    _row("Snap", "Invoker", 100, 100), _row("Snap", "Acolyte of Chayula", 90, 90),
    _row("Arc", "Invoker", 40, 140, "Wand"), _row("Arc", "Acolyte of Chayula", 35, 35, "Wand")]}


def test_plan_picks_the_best_and_adds_a_boss_skill():
    plan = plan_build(RESULT)
    assert plan["spec"]["skill"] == "Snap" and plan["spec"]["ascendancy"] == "Invoker"
    assert plan["spec"]["boss_skill"] == "Arc" and plan["spec"]["boss_weapon_type"] == "Wand"
    assert plan["vs_recommended"] == 0 and plan["note"] is None


def test_feedback_lock_reports_the_cost():
    plan = plan_build(RESULT, ascendancy="Acolyte of Chayula")
    assert plan["spec"]["ascendancy"] == "Acolyte of Chayula"
    assert plan["vs_recommended"] == pytest.approx(0.10)
    assert "10% less damage" in plan["note"]
    assert "boss_skill" not in plan["spec"], "Arc on Acolyte doesn't hit 25% harder, so no boss skill"
    with pytest.raises(ValueError):
        plan_build(RESULT, ascendancy="Lich")


def test_options_list_each_alternative_once():
    opts = options(RESULT)
    assert [o["ascendancy"] for o in opts["ascendancies"]] == ["Invoker", "Acolyte of Chayula"]
    assert [o["skill"] for o in opts["skills"]] == ["Snap", "Arc"]


def test_conditions_follow_what_the_build_does(pob):
    pob.new()
    pob.set_class("Huntress", "Amazon")
    pob.set_level(90)
    pob.add_item(SPEAR)
    pob.add_skill(["Rake"])
    applied = {a["var"] for a in pob.auto_config("bossing")}
    assert {"conditionHitRecently", "conditionEnemyBleeding"} <= applied
    assert "conditionKilledRecently" not in applied, "bossing: no kills to count"
    assert "conditionEnemyShocked" not in applied, "Rake does not shock"
    assert "conditionKilledRecently" in {a["var"] for a in pob.auto_config("mapping")}


def test_spirit_adds_a_buff_within_budget(pob, monk, catalog):
    before = pob.calc(["FullDPS", "TotalDPS", "SpiritUnreserved"])
    chosen = optimise_spirit(pob, catalog, log=lambda *a: None)
    after = pob.calc(["FullDPS", "TotalDPS", "SpiritUnreserved"])
    assert chosen, "a level 90 Monk with 100 spirit should find at least one useful buff"
    assert after["SpiritUnreserved"] >= 0
    assert max(after.get("FullDPS", 0), after["TotalDPS"]) > max(before.get("FullDPS", 0), before["TotalDPS"])


def test_boss_skill_on_weapon_set_two(pob, monk):
    boss = pob.add_skill(["Spark"], main=False, full_dps=True)["group"]
    pob.send("set_weapon_set", group=boss, set=2)
    pob.send("set_main", group=boss)
    plan = craft_weapon(pob, make_stage("mid", "medium"), "Weapon 1 Swap", "Wand", log=lambda *a: None)
    assert plan.base and plan.affixes
    assert pob.calc(["TotalDPS"]).get("TotalDPS", 0) > 0, "Spark uses the swap wand"
    pob.send("set_main", group=monk)
    assert pob.calc(["TotalDPS"]).get("TotalDPS", 0) > 0, "Tempest Flurry still uses the staff"
