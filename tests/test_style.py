"""Play style on the forge (NIGHT_TASKS 9): best / one button / combo setup, in generate.plan_build."""
from generate import combo_for, plan_build


def row(skill, cls="Warrior", asc="Titan", w="Two Hand Mace", score=100.0, boss=100.0, clear=100.0):
    return {"skill": skill, "cls": cls, "ascendancy": asc, "weapon_type": w, "weapon_subtype": None,
            "offhand_type": None, "score": score, "dps": boss, "boss": boss, "clear": clear}


def result(style, ranked):
    return {"ranked": ranked, "searched": {"style": style} if style else {}}


RANKED = [row("Rend", score=100, boss=100, clear=100),
          row("Hammer of the Gods", score=90, boss=400, clear=20),
          row("Sunder", score=80, boss=50, clear=300)]


def test_best_keeps_boss_and_clear_skills():
    spec = plan_build(result(None, RANKED))["spec"]
    assert spec["skill"] == "Rend" and spec.get("boss_skill") == "Hammer of the Gods" and spec.get("clear_skill") == "Sunder"
    assert "combo" not in spec


def test_one_button_is_one_skill():
    spec = plan_build(result("one", RANKED))["spec"]
    assert spec["skill"] == "Rend" and "boss_skill" not in spec and "clear_skill" not in spec


def _with_combo():
    """A payoff in the combo data that a Titan with a two-handed mace can set up (the data is re-run now and then:
    on 2026-11-25 Rend's best setups became Talisman, Bow and Spear skills, so no fixed skill name here)."""
    from generate import _combo_data
    for r in _combo_data()["rows"]:
        rows = [row(r["payoff"])] + RANKED[1:]
        if combo_for(rows[0], {}):
            return rows
    raise AssertionError("no combo in data/breaker/combos.json a Titan can use")


def test_combo_adds_a_setup_from_the_combo_finder():
    ranked = _with_combo()
    c = combo_for(ranked[0], {})
    assert c and c["condition"] == "Armour Broken" and c["edge"] > 0 and 0 < c["uptime"] <= 1
    spec = plan_build(result("combo", ranked))["spec"]
    assert spec.get("combo") and "boss_skill" not in spec   # the combo is the boss plan


def test_combo_falls_back_with_a_note():
    ranked = [row("Fireball", cls="Witch", asc="Infernalist", w="Wand")]
    spec = plan_build(result("combo", ranked))["spec"]
    assert "combo" not in spec and "No setup" in spec["combo_note"]


def test_style_is_on_the_spec():
    assert plan_build(result("one", RANKED))["spec"]["style"] == "one"
    assert "style" not in plan_build(result(None, RANKED))["spec"]
