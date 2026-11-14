"""Accuracy check: load a PoB code in the headless engine and print the numbers PoB's own window shows.

Usage (inside the Docker image, from the repo root on the PC):
    docker run --rm -i poe2-optimizer python engine/tools/accuracy_check.py < my_build.txt

my_build.txt holds one PoB share code (from PoB: Import/Export Build > Generate, or a pobb.in link's code).
Open the same code in the Path of Building app, keep the same main skill selected, and compare each line
with PoB's sidebar. The engine loads the code exactly as saved (config, enemy, main skill), so any gap
is an engine bug or a PoB version difference: the version line at the top must match the app's.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from compare import FIELDS  # noqa: E402
from optimize import total_dps  # noqa: E402
from pob import PoB  # noqa: E402

# What PoB's sidebar calls each stat, so the two are easy to read side by side.
LABELS = {
    "TotalDPS": "Hit DPS (Total DPS)", "CombinedDPS": "Combined DPS", "FullDPS": "Full DPS",
    "TotalDotDPS": "Total DoT DPS", "BleedDPS": "Bleed DPS", "PoisonDPS": "Poison DPS", "IgniteDPS": "Ignite DPS",
    "MinionDPS": "Minion DPS", "MinionDotDPS": "Minion DoT DPS", "AverageHit": "Average Hit",
    "Speed": "Attack/Cast Rate", "HitChance": "Hit Chance %", "CritChance": "Crit Chance %",
    "CritMultiplier": "Crit Multiplier", "Life": "Life", "EnergyShield": "Energy Shield", "Mana": "Mana",
    "Armour": "Armour", "Evasion": "Evasion", "TotalEHP": "Effective Hit Pool",
    "PhysicalMaximumHitTaken": "Phys Max Hit", "FireResist": "Fire Res", "ColdResist": "Cold Res",
    "LightningResist": "Lightning Res", "ChaosResist": "Chaos Res",
}


def main() -> int:
    code = (sys.argv[1] if len(sys.argv) > 1 else sys.stdin.read()).strip()
    if not code:
        print(__doc__)
        return 2
    with PoB() as pob:
        pob.load_code(code)
        main_skill = pob.send("calc", fields=["TotalDPS"]).get("main_skill")
        stats = pob.calc(FIELDS)
        version = pob.version
    print(f"PoB version in engine: {version}")
    print(f"Main skill: {main_skill}\n")
    for f in FIELDS:
        v = stats.get(f)
        if v is None:
            continue
        print(f"{LABELS.get(f, f):<22} {v:>14,.1f}")
    print(f"\n{'Our headline DPS':<22} {total_dps(stats):>14,.1f}   (hit + DoT, or Full DPS; not a PoB sidebar line)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
