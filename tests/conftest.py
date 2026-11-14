import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "engine"))
sys.path.insert(0, str(ROOT))

from pob import PoB  # noqa: E402

STAFF = "Rarity: Rare\nTest Staff\nWyrm Quarterstaff\nAdds 20 to 300 Lightning Damage\nAdds 50 to 90 Physical Damage\n25% increased Attack Speed"
SPEAR = "Rarity: Rare\nTest Spear\nAkoyan Spear\nAdds 60 to 140 Physical Damage\n150% increased Physical Damage"


@pytest.fixture(scope="session")
def pob():
    with PoB() as p:
        yield p


@pytest.fixture
def monk(pob):
    """Fresh level 90 Invoker with a staff and Tempest Flurry. Returns the skill group."""
    pob.new()
    pob.set_class("Monk", "Invoker")
    pob.set_level(90)
    pob.add_item(STAFF)
    return pob.add_skill(["Tempest Flurry"])["group"]
