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
