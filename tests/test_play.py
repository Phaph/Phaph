"""Skills used instead of each other (main / boss / clear / combo setup) are never summed in Full DPS."""
import pytest

from guide import score_combo
from optimize import total_dps

F = ["TotalDPS", "TotalDotDPS", "FullDPS", "MinionDPS", "MinionDotDPS"]
MACE = "Rarity: Rare\nTest Mace\nMarauding Mace\nAdds 100 to 200 Physical Damage"


@pytest.fixture
def two(pob):
    pob.new()
    pob.set_class("Warrior", "Titan")
    pob.set_level(90)
    pob.add_item(MACE)
    main = pob.add_skill(["Boneshatter"])["group"]
    setup = pob.add_skill(["Armour Breaker"], main=False)["group"]
    alone = {}
    for g in (main, setup):
        pob.send("set_main", group=g)
        alone[g] = total_dps(pob.calc(F))
    pob.send("set_main", group=main)
    return main, setup, alone


def test_only_the_played_skill_counts(pob, two):
    main, setup, alone = two
    pob.use_full_dps()   # optimise_spirit does this on every build
    for g in (main, setup, main):
        pob.send("set_main", group=g)
        assert total_dps(pob.calc(F)) == pytest.approx(alone[g], rel=0.01)


def test_combo_setup_dps_is_the_setups_own(pob, two):
    main, setup, alone = two
    pob.use_full_dps()
    combo, _ = score_combo(pob, main, setup, {"setup": "Armour Breaker"}, False)
    assert combo["alone"] == pytest.approx(alone[main], rel=0.01)
    if "setup_dps" in combo:
        assert combo["setup_dps"] == pytest.approx(alone[setup], rel=0.01)


def test_heralds_and_minions_add(pob, two):
    main, setup, alone = two
    pob.add_skill(["Raging Spirits"], main=False, full_dps=True)
    pob.use_full_dps()
    assert total_dps(pob.calc(F)) > alone[main] * 1.05


def test_boss_skill_never_adds_to_the_main_skill(pob, two):
    main, setup, alone = two
    boss = pob.add_skill(["Rolling Slam"], main=False, full_dps=True)["group"]
    pob.use_full_dps()
    assert total_dps(pob.calc(F)) == pytest.approx(alone[main], rel=0.01)
    pob.send("set_main", group=boss)
    pob.use_full_dps()
    own = total_dps(pob.calc(F))
    pob.send("set_main", group=main)
    assert own > 0 and total_dps(pob.calc(F)) == pytest.approx(alone[main], rel=0.01)
