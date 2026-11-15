"""Prompt mode parser. No PoB needed: uses a small fake catalog."""
from prompt import divines_to_budget, parse_prompt

CATALOG = {
    "classes": [
        {"name": "Monk", "ascendancies": ["Invoker", "Acolyte of Chayula"]},
        {"name": "Witch", "ascendancies": ["Infernalist", "Blood Mage", "Lich"]},
        {"name": "Ranger", "ascendancies": ["Deadeye", "Pathfinder"]},
    ],
    "skills": ["Lightning Arrow", "Tempest Flurry", "Raise Zombie", "Fireball", "Spark"],
    "weapon_types": {"Bow": [], "Dagger": [], "Staff": ["Warstaff"], "One Hand Mace": [], "Two Hand Mace": []},
}


def parse(text):
    return parse_prompt(text, CATALOG)["request"]


def test_example_prompt():
    r = parse("lightning minion build for a monk, 5 div")
    assert r["damage"] == ["lightning"]
    assert r["kinds"] == ["minion"]
    assert r["class"] == "Monk"
    assert r["budget"] == "budget"


def test_currency_amounts():
    assert parse("30 divines")["budget"] == "medium"
    assert parse("50div")["budget"] == "high"
    assert parse("300 ex")["budget"] == "budget"           # under a divine
    assert parse("2k chaos poison build")["budget"] == "unlimited"
    assert "chaos" not in parse("20 chaos fire build")["damage"]
    assert divines_to_budget(0) == "free" and divines_to_budget(100) == "high" and divines_to_budget(101) == "unlimited"


def test_budget_words():
    assert parse("league starter")["budget"] == "budget"
    assert parse("ssf witch")["budget"] == "free"
    assert parse("high budget bow")["budget"] == "high"
    assert parse("mirror tier spark")["budget"] == "unlimited"
    assert "budget" not in parse("fire spells")


def test_skill_ascendancy_and_class():
    r = parse("Lightning Arrow deadeye")
    assert r["skill"] == "Lightning Arrow" and r["ascendancy"] == "Deadeye" and r["class"] == "Ranger"
    assert parse("blood mage bleed")["ascendancy"] == "Blood Mage"
    assert parse("something for witches")["class"] == "Witch"


def test_ailment_weapon_goals_mode():
    r = parse("tanky dagger bleed bosser that's fast")
    assert r["ailment"] == "bleed"
    assert r["weapons"] == ["Dagger"]
    assert set(r["goals"]) == {"tanky", "movement"}
    assert r["mode"] == "bossing"
    assert parse("mace slam")["weapons"] == ["One Hand Mace", "Two Hand Mace"]
    assert "mode" not in parse("good at maps and bosses")      # both: stay balanced


def test_negation():
    r = parse("cold spells, no minions")
    assert r["kinds"] == ["spell"]
    assert r["damage"] == ["cold"]


def test_found_lists_what_was_understood():
    out = parse_prompt("fire totem witch", CATALOG)
    means = [f["means"] for f in out["found"]]
    assert "Damage: fire" in means and "Kind: totem" in means and "Class: Witch" in means
    assert out["budget_set"] is False


def test_deep_search_prompts():
    r = parse("any build highest dps possible in the game")
    assert r.get("deep") is True and r["budget"] == "unlimited" and r["mode"] == "bossing"
    r = parse("strongest build for a monk, 10 div")
    assert r.get("deep") is True and r["budget"] == "medium" and r["class"] == "Monk"   # a named budget wins
    assert parse("highest damage witch").get("budget") is None                           # no "possible": budget untouched


def test_normal_prompts_stay_normal():
    for text in ("lightning minion build for a monk, 5 div", "best build for mapping", "cheap fast bleed build",
                 "fireball witch that can boss"):
        assert not parse(text).get("deep"), text


def test_every_named_skill_is_kept():
    cat = {**CATALOG, "skills": CATALOG["skills"] + ["Cast on Elemental Ailment", "Charged Staff"],
           "helper_skills": ["Cast on Elemental Ailment", "Charged Staff"]}
    r = parse_prompt("warrior spark cast on elemental ailment", cat)["request"]
    assert r["skill"] == "Spark" and r["with_skills"] == ["Cast on Elemental Ailment"]
    assert "spell" not in r["kinds"], "'cast' inside a skill name isn't a kind of skill"
    r = parse_prompt("charged staff monk", cat)["request"]
    assert not r.get("skill") and r["with_skills"] == ["Charged Staff"]


def test_skills_match_the_way_players_type_them():
    cat = {**CATALOG, "skills": CATALOG["skills"] + ["Cast on Critical", "Cast on Elemental Ailment", "Comet"],
           "helper_skills": ["Cast on Critical", "Cast on Elemental Ailment"]}
    cases = {
        "sparks, cast on crit, 1000 div": ("Spark", ["Cast on Critical"]),
        "spark coc": ("Spark", ["Cast on Critical"]),
        "comets with cast on critical": ("Comet", ["Cast on Critical"]),
        "cast on crit comet": ("Comet", ["Cast on Critical"]),
        "lightning arrows": ("Lightning Arrow", None),
        "raise zombies": ("Raise Zombie", None),
    }
    for text, (skill, helpers) in cases.items():
        r = parse_prompt(text, cat)["request"]
        assert r.get("skill") == skill and r.get("with_skills") == helpers, (text, r)
        assert "spell" not in r["kinds"], text
