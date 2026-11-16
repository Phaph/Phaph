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


def test_theme_metric_drives_every_optimiser():
    """Regression: a bleed request came back as an elemental hit build, because only skill
    choice saw the theme. Every optimiser now scores with the same theme metric."""
    from optimize import metric_for, score_of
    out = {"BleedDPS": 1000, "TotalDPS": 4000, "AreaOfEffectMod": 4}
    assert metric_for("mapping", "bleed") == "bleed+mapping"
    assert metric_for("bossing", None) == "total"
    # bleed fully, hits a quarter; this build is 20% bleed, half the 40% target, so it scores half
    assert score_of(out, "bleed") == (1000 + 0.25 * 4000) * 0.5
    assert score_of(out, "bleed+mapping") == score_of(out, "bleed") * 2
    hits_only = {"BleedDPS": 0, "TotalDPS": 6000}
    assert score_of(hits_only, "bleed") < score_of(out, "bleed"), "bleed beats more raw hit damage"


def test_goals_trade_damage_for_speed_and_loot(pob, catalog):
    from gear import craft_gear, make_stage
    from goals import mobility_skills, weights
    with pytest.raises(ValueError):
        weights(["fishing"])
    stage = make_stage("mid", "medium")
    fields = ["EffectiveMovementSpeedMod", "EffectiveLootRarityMod"]
    results = {}
    for goals in (None, ["movement", "rarity"]):
        pob.new()
        pob.set_class("Monk", "Invoker")
        pob.set_level(90)
        pob.add_skill(["Tempest Flurry"])
        craft_gear(pob, stage, "Staff", "Warstaff", goals=goals, uniques=False, log=lambda *a: None)
        results[bool(goals)] = pob.calc(fields)
    assert results[True]["EffectiveMovementSpeedMod"] > results[False]["EffectiveMovementSpeedMod"] + 0.1
    assert results[True]["EffectiveLootRarityMod"] > results[False]["EffectiveLootRarityMod"]
    assert mobility_skills(catalog, "Staff"), "every build gets a movement skill suggestion"


def test_theme_check_flags_off_theme_builds(catalog):
    from themes import check
    spec = {"skill": "Rake", "ailment": "bleed", "damage": ["physical"]}
    assert check(spec, {"TotalDPS": 1000, "BleedDPS": 900}, catalog) == []
    issues = check(spec, {"TotalDPS": 1000, "BleedDPS": 50}, catalog)
    assert issues and "bleed" in issues[0]
    assert check({"skill": "Rake", "damage": ["lightning"]}, {"TotalDPS": 1}, catalog)


def test_rating_scale():
    from rating import anchors, rate
    cal = {"damage": anchors([1e5, 2e5, 4e5, 8e5, 2e6]), "clear": anchors([1e5, 3e5, 9e5]),
           "toughness": anchors([5e3, 1e4, 2e4, 4e4])}
    mid = rate(4e5, 3e5, 1.4e4, cal)
    assert 4 <= mid["overall"] <= 6 and mid["label"] in ("Solid", "Strong")
    assert rate(1e3, 1e3, 1e3, cal)["overall"] < 2
    top = rate(1e7, 5e6, 1e5, cal)
    assert top["overall"] == 10 and top["label"] == "Broken"


def test_utility_skills_raise_main_damage(pob, catalog):
    from utility import optimise_utility
    pob.new()
    pob.set_class("Huntress", "Amazon")
    pob.set_level(90)
    pob.add_item(SPEAR)
    pob.add_skill(["Rake"])
    before = pob.calc(["BleedDPS"]).get("BleedDPS", 0)
    kept = optimise_utility(pob, catalog, "Spear", "bleed", log=lambda *a: None)
    assert kept and all(k["gain"] > 0.03 for k in kept)
    assert pob.calc(["BleedDPS"]).get("BleedDPS", 0) > before


def test_search_closes_its_pob_processes():
    """Regression: a search left its worker PoB processes running (17 GB after one search)."""
    import generate
    from generate import _close_all, _bind, _pob
    from concurrent.futures import ThreadPoolExecutor
    mine = []
    with ThreadPoolExecutor(2, initializer=_bind, initargs=(mine,)) as pool:
        list(pool.map(lambda _: _pob().send("new"), range(4)))
    assert 1 <= len(mine) <= 2
    _close_all(mine)
    assert all(p.proc.poll() is not None for p in mine)


def test_deep_search_scouts_each_skills_own_ascendancies(monkeypatch):
    """Deep search: a wider pool re-scored with passives, then each finalist on its own best ascendancies.
    A normal search never calls the scout."""
    import generate as g

    skills = [{"name": f"Skill{i}", "types": ["Spell"], "weapons": []} for i in range(30)]
    classes = [{"name": "Witch", "ascendancies": ["A1", "A2", "A3", "A4"]},
               {"name": "Monk", "ascendancies": ["B1", "B2", "B3", "B4"]}]

    class FakePoB:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def send(self, cmd, **k): return {"skills": skills}
        def list_classes(self): return classes
        def close(self): pass

    def fake_eval(c, stage, req, tree):
        n = int(c.skill[5:])
        # Without passives the low numbers look best; with passives Skill20-23 (still inside the deep pool) win.
        c.score = (1000 + n * 100 if n >= 20 else 500) if tree else 100 - n
        if c.ascendancy:
            c.score += {"A1": 1, "B4": 50}.get(c.ascendancy, 0)
        return c

    scouted = []

    def fake_scout(f, ascs, stage, req, keep=3):
        scouted.append(f.skill)
        return [("Monk", "B4"), ("Witch", "A1"), ("Monk", "B1")]

    monkeypatch.setattr(g, "PoB", FakePoB)
    monkeypatch.setattr(g, "evaluate", fake_eval)
    monkeypatch.setattr(g, "scout_ascendancies", fake_scout)
    monkeypatch.setattr(g, "main_skills", lambda cat, req: skills)
    monkeypatch.setattr(g, "weapon_options", lambda s, req: [("Wand", None, None)])

    normal = g.generate({}, workers=2, log=lambda *a: None)
    assert not scouted
    assert normal["ranked"][0]["skill"] in {f"Skill{i}" for i in range(4)}   # only round 1's top 4 went on

    deep = g.generate({"deep": True}, workers=2, log=lambda *a: None)
    assert len(scouted) == g.DEEP_SKILLS
    assert deep["ranked"][0]["skill"] == "Skill23" and deep["ranked"][0]["ascendancy"] == "B4"


def test_a_named_buff_is_kept_as_a_helper(monkeypatch):
    """'charged staff' is a buff, not a damage skill: keep it in every build, lock its weapon, and pick the best
    skill to pair it with, instead of dropping the weapon and then the skill."""
    import generate as g

    cat = [{"name": "Charged Staff", "types": ["Buff", "Spell"], "weapons": ["Staff"]},
           {"name": "Tempest Flurry", "types": ["Attack", "Melee"], "weapons": ["Staff"]}]

    class FakePoB:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def send(self, cmd, **k): return {"skills": cat}

    seen = {}

    def fake_once(req, workers, top_skills, log, progress):
        seen.update(req)
        return {"ranked": []}

    monkeypatch.setattr(g, "PoB", FakePoB)
    monkeypatch.setattr(g, "_generate_once", fake_once)
    out = g.generate({"skill": "Charged Staff", "budget": "high"}, log=lambda *a: None)
    assert seen.get("with_skills") == ["Charged Staff"] and not seen.get("skill")
    assert seen.get("weapons") == ["Staff"] and seen.get("_attack_only")
    # ...so a staff spell can't be paired with it, only staff attacks.
    names = [x["name"] for x in g.main_skills(cat + [{"name": "Hexblast", "types": ["Spell", "Damage"], "weapons": []}], seen)]
    assert names == ["Tempest Flurry"]
    assert out["relaxed"] and "kept in the build" in out["relaxed"][0]
    assert out["searched"]["with_skills"] == ["Charged Staff"]


def test_named_spell_with_a_cast_on_x_gem(monkeypatch):
    """'warrior spark cast on elemental ailment': Spark stays the main skill, the Cast on X gem is kept with Spark
    socketed in it, and only spells can be the main skill when a Cast on X gem is asked for."""
    import generate as g

    cat = [{"name": "Spark", "types": ["Spell", "Lightning"], "weapons": []},
           {"name": "Cast on Elemental Ailment", "types": ["Meta", "Buff", "Persistent"], "weapons": []},
           {"name": "Tempest Flurry", "types": ["Attack", "Melee"], "weapons": ["Staff"]}]

    class FakePoB:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def send(self, cmd, **k): return {"skills": cat}

    seen = {}
    monkeypatch.setattr(g, "PoB", FakePoB)
    monkeypatch.setattr(g, "_generate_once", lambda req, *a: seen.update(req) or {"ranked": []})
    out = g.generate({"skill": "Spark", "with_skills": ["Cast on Elemental Ailment"], "class": "Warrior"}, log=lambda *a: None)
    assert seen["skill"] == "Spark" and seen["with_skills"] == ["Cast on Elemental Ailment"]
    assert seen["_metas"] == ["Cast on Elemental Ailment"] and seen["_spell_only"]
    assert [x["name"] for x in g.main_skills(cat, {"_spell_only": True})] == ["Spark"]
    assert "socketed" in out["relaxed"][0]

    groups = []

    class Rec:
        def add_skill(self, gems, main=True, **k): groups.append(gems)
    g.add_helpers(Rec(), seen, "Spark")
    assert groups == [["Spark", "Cast on Elemental Ailment"]]


def test_avoid_keeps_kind_out_of_main_skills():
    from generate import main_skills
    cat = [{"name": "Raise Zombie", "types": ["Minion", "Physical"], "weapons": []},
           {"name": "Fireball", "types": ["Spell", "Fire", "Projectile"], "weapons": []}]
    assert [s["name"] for s in main_skills(cat, {"avoid": ["minion"]})] == ["Fireball"]
    assert [s["name"] for s in main_skills(cat, {"avoid": ["fire"]})] == ["Raise Zombie"]


def test_totem_means_a_skill_that_summons_a_totem():
    # "Totemable" only means a totem *could* use the skill (Sunder); a totem build needs a skill that places one.
    from generate import main_skills
    cat = [{"name": "Sunder", "types": ["Attack", "Melee", "Slam", "Totemable", "Physical"], "weapons": ["Two Hand Mace"]},
           {"name": "Shockwave Totem", "types": ["Attack", "SummonsTotem", "Slam", "Physical"], "weapons": ["Two Hand Mace"]}]
    assert [s["name"] for s in main_skills(cat, {"kinds": ["totem"]})] == ["Shockwave Totem"]


def test_block_build_holds_a_shield():
    from generate import weapon_options
    spell = {"name": "Fireball", "types": ["Spell", "Fire"], "weapons": []}
    assert weapon_options(spell, {"goals": ["block"]}) == [("Wand", None, "Shield")]
    bow = {"name": "Lightning Arrow", "types": ["Attack", "Lightning"], "weapons": ["Bow"]}
    assert weapon_options(bow, {"goals": ["block"]}) == []   # a bow can't go with a shield: not a block build


def test_tree_granted_skills_are_not_picked():
    # Virtuous Barrier comes from a Gemling Legionnaire passive: the catalog marks it from_item, and no picker uses it.
    from spirit import spirit_candidates
    cat = [{"name": "Virtuous Barrier", "types": ["Buff", "Persistent"], "spirit": 30, "from_item": True, "weapons": []},
           {"name": "Wind Dancer", "types": ["Buff", "Persistent"], "spirit": 30, "weapons": []}]
    assert spirit_candidates(cat, minion_build=False) == ["Wind Dancer"]


def test_defence_candidates_are_defensive_buffs_only():
    from defence import defence_candidates
    cat = [{"name": "Wind Dancer", "types": ["Buff", "Persistent"], "spirit": 30, "weapons": []},
           {"name": "Herald of Ice", "types": ["Buff", "Persistent", "Herald", "Damage"], "spirit": 30, "weapons": []},
           {"name": "Virtuous Barrier", "types": ["Buff", "Persistent"], "spirit": 0, "from_item": True, "weapons": []}]
    assert defence_candidates(cat) == ["Wind Dancer"]


def test_plan_adds_a_clear_skill_on_the_same_weapon():
    rows = [_row("Whirlwind Lance", "Invoker", 100, 100, "Spear") | {"clear": 50},
            _row("Glacial Lance", "Invoker", 80, 60, "Spear") | {"clear": 90},
            _row("Fireball", "Invoker", 70, 50, "Wand") | {"clear": 200}]   # better clear, but another weapon
    plan = plan_build({"request": {"budget": "high"}, "ranked": rows})
    assert plan["spec"]["clear_skill"] == "Glacial Lance"
    assert "clear_skill" not in plan_build(RESULT)["spec"]   # no "clear" numbers: no clear skill


def test_totem_build_offers_skills_a_totem_gem_places():
    from generate import main_skills
    cat = [{"name": "Fireball", "types": ["Spell", "Fire", "Totemable"], "weapons": []},
           {"name": "Boneshatter", "types": ["Attack", "Melee", "Totemable", "Physical"], "weapons": ["One Hand Mace", "Two Hand Mace"]},
           {"name": "Lightning Arrow", "types": ["Attack", "Lightning", "Totemable"], "weapons": ["Bow"]},
           {"name": "Spell Totem", "types": ["Meta", "SummonsTotem"], "weapons": []},
           {"name": "Ancestral Warrior Totem", "types": ["Meta", "SummonsTotem"], "weapons": ["One Hand Mace", "Two Hand Mace"]}]
    got = {s["name"]: s.get("totem") for s in main_skills(cat, {"kinds": ["totem"]})}
    assert got == {"Fireball": "Spell Totem", "Boneshatter": "Ancestral Warrior Totem"}   # no totem for bows
    assert [s["name"] for s in main_skills(cat, {"kinds": ["totem"], "_totem_gem": "Spell Totem"})] == ["Fireball"]
    assert [s["name"] for s in main_skills(cat, {})] == ["Fireball", "Boneshatter", "Lightning Arrow"]   # self-cast


def test_pob_client_puts_the_totem_gem_in_front():
    from pob import PoB
    p = PoB.__new__(PoB)
    p.totem_for = {"Fireball": "Spell Totem"}
    assert p._with_totem(["Fireball", "Spell Echo"]) == ["Spell Totem", "Fireball", "Spell Echo"]
    assert p._with_totem(["Frostbolt"]) == ["Frostbolt"]
