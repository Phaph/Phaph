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
