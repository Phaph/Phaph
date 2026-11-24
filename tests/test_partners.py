"""Partner combos (engine/partners.py): Twister scored through Whirling Slash's whirlwind."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))

from partners import PARTNERS, cycle_dps  # noqa: E402


def test_cycle_alone_is_payoff():
    assert cycle_dps(0, 1000, 1.4, 2000, 2.0) == 2000


def test_cycle_mixes_setup_and_payoff_time():
    # 3 slashes at 1.4/s (1445 per slash), then one Twister at 2/s dealing 4x its 1125-per-use base
    d = cycle_dps(3, 2023, 1.4, 4 * 2250, 2.0)
    damage = 3 * 2023 / 1.4 + 4 * 2250 / 2.0
    assert abs(d - damage / (3 / 1.4 + 0.5)) < 1e-6
    assert d > 2250   # worth it: beats Twister alone


def test_cycle_not_worth_it_when_payoff_barely_grows():
    assert cycle_dps(3, 100, 1.0, 2100, 2.0) < 2000


def test_twister_rule():
    r = PARTNERS["Twister"]
    assert r["setup"] == "Whirling Slash" and r["var"] == "whirlwindStages" and r["max"] == 3


def test_infusion_cycle():
    from partners import infusion_cycle
    # Ice Nova: 1.84 casts/s, x3.75 infused, Frost Bomb every 6 s -> about +16%
    plain, speed = 8186, 1.84
    c = infusion_cycle(3.75 * plain, plain, speed, 6.0)
    assert 1.10 < c / plain < 1.25
    assert infusion_cycle(3 * plain, plain, speed, 0) == plain


def test_extra_sets_only_always_landing_parts():
    from partners import EXTRA_SETS
    assert EXTRA_SETS["Earthquake"] == [2] and EXTRA_SETS["Fireball"] == [2]
    for conditional in ("Frost Darts", "Lightning Spear", "Explosive Spear", "Glacial Lance", "Incinerate"):
        assert conditional not in EXTRA_SETS


def test_extra_sets_add_up(pob):
    """Earthquake's Aftershock (stat set 2) is added to the impact (set 1)."""
    from partners import apply_extra_sets
    pob.new()
    pob.set_class("Warrior", None)
    pob.set_level(60)
    pob.add_item("Rarity: NORMAL\nWooden Club\nWooden Club")
    g = pob.add_skill(["Earthquake"])["group"]
    fields = ["TotalDPS", "TotalDotDPS", "Speed"]
    out = pob.calc(fields)
    scaled, note = apply_extra_sets(pob, "Earthquake", g, out, fields)
    assert note and scaled["TotalDPS"] > 2 * out["TotalDPS"]
    assert pob.send("set_part", group=g)["part"] == 1     # left on set 1


def test_frost_bomb_exposure_helps_a_plain_cold_spell(pob):
    """Frost Bomb's Elemental Exposure (a debuff from any active skill) raises Comet's damage; its cast time is paid."""
    from partners import apply_exposure
    pob.new()
    pob.set_class("Sorceress", None)
    pob.set_level(90)
    pob.add_item("Rarity: NORMAL\nAshen Staff\nAshen Staff")
    g = pob.add_skill(["Comet"])["group"]
    fields = ["TotalDPS", "TotalDotDPS", "Speed"]
    out = pob.calc(fields)
    scaled, note = apply_exposure(pob, "Comet", g, out, fields, [])
    assert note and note["setup"] == "Frost Bomb" and 1.02 < note["factor"] < 1.2
    assert pob.calc(fields)["TotalDPS"] == out["TotalDPS"]      # the build is left as it was


def test_no_hit_part_adds_only_its_damage_over_time(pob):
    """Poisonburst Arrow's burst deals no hit: PoB repeats the arrow's hit for it (read as x2 until 2026-11-24)."""
    from partners import apply_extra_sets
    F = ["TotalDPS", "TotalDotDPS", "FullDPS", "MinionDPS", "MinionDotDPS"]
    pob.new()
    pob.set_class("Ranger", "Deadeye")
    pob.set_level(90)
    pob.add_item("Rarity: Rare\nT\nGemini Bow\nAdds 100 to 200 Physical Damage")
    g = pob.add_skill(["Poisonburst Arrow"])["group"]
    out = pob.calc(F)
    scaled, note = apply_extra_sets(pob, "Poisonburst Arrow", g, out, F)
    assert out["TotalDPS"] > 0 and note and note["factor"] < 1.9


def test_extra_part_does_not_count_minions_again(pob):
    from optimize import total_dps
    from partners import apply_extra_sets
    F = ["TotalDPS", "TotalDotDPS", "FullDPS", "MinionDPS", "MinionDotDPS"]
    pob.new()
    pob.set_class("Sorceress", "Stormweaver")
    pob.set_level(90)
    g = pob.add_skill(["Fireball"])["group"]
    own = pob.calc(F)["TotalDPS"]
    pob.add_skill(["Raging Spirits"], main=False, full_dps=True)
    pob.use_full_dps()
    out = pob.calc(F)
    scaled, _ = apply_extra_sets(pob, "Fireball", g, out, F)
    assert total_dps(scaled) - total_dps(out) <= own * 1.05
