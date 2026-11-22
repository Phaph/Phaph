"""Leveling rule (leveling.choose): endgame skill as soon as it's close, swaps only when clearly better, max 3."""
from leveling import choose


def test_endgame_skill_from_act1_when_it_is_fine():
    sc = {"act1": {"Bonestorm": 90, "Spark": 100}, "act2": {"Bonestorm": 95, "Spark": 100}}
    plan, why = choose(sc, "Bonestorm")
    assert plan == {}                      # no leveling skill needed


def test_one_leveling_skill_then_the_endgame_skill():
    sc = {"act1": {"Spark": 100}, "act2": {"Spark": 100, "Arc": 110}, "act34": {"Spark": 100, "Arc": 120, "Comet": 115}}
    plan, why = choose(sc, "Comet")
    assert plan == {"act1": "Spark", "act2": "Spark"}   # Arc +10% / +20%: not worth a swap; Comet within 20% at act34


def test_swap_when_much_better_and_never_more_than_three():
    sc = {"act1": {"A": 100}, "act2": {"A": 100, "B": 140}, "act34": {"A": 100, "B": 140, "C": 300},
          "interludes": {"A": 100, "B": 140, "C": 300, "E": 200}}
    plan, why = choose(sc, "E")
    assert plan["act1"] == "A" and plan["act2"] == "B"
    assert len(set(plan.values()) | {"E"}) <= 3
