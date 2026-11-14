"""Compare tree optimiser settings on a few fixed builds: DPS, EHP and seconds for each.

Run inside the engine image:  python engine/tools/tree_bench.py
The "old" row is the build phase only with the old 6-point reach; "new" adds the long
reach for notables and keystones plus the swap phase.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from optimize import score_of  # noqa: E402
from pob import PoB  # noqa: E402

STAFF = "Rarity: Rare\nTest Staff\nWyrm Quarterstaff\nAdds 20 to 300 Lightning Damage\nAdds 50 to 90 Physical Damage\n25% increased Attack Speed"
SPEAR = "Rarity: Rare\nTest Spear\nAkoyan Spear\nAdds 60 to 140 Physical Damage\n150% increased Physical Damage"
SCEPTRE = "Rarity: Rare\nTest Sceptre\nOmen Sceptre\n+2 to Level of all Minion Skills\n+150 to Spirit"
WAND = "Rarity: Rare\nTest Wand\nAttuned Wand\n+3 to Level of all Spell Skills\n80% increased Spell Damage"

BUILDS = [
    ("Monk Invoker, Tempest Flurry", "Monk", "Invoker", [STAFF], ["Tempest Flurry"], "total"),
    ("Witch Infernalist, Skeletal Storm Mage", "Witch", "Infernalist", [SCEPTRE], ["Skeletal Storm Mage"], "total"),
    ("Sorceress Stormweaver, Spark", "Sorceress", "Stormweaver", [WAND], ["Spark"], "total"),
    ("Huntress Amazon, spear Twister", "Huntress", "Amazon", [SPEAR], ["Twister"], "total"),
]
FIELDS = ["TotalDPS", "TotalDotDPS", "FullDPS", "FullDotDPS", "BleedDPS", "PoisonDPS", "IgniteDPS", "TotalEHP",
          "MinionDPS", "MinionDotDPS"]


def setup(pob, cls, asc, items, gems):
    pob.new()
    pob.set_class(cls, asc)
    pob.set_level(90)
    for raw in items:
        pob.add_item(raw)
    pob.add_skill(gems)


def main():
    with PoB() as pob:
        for name, cls, asc, items, gems, metric in BUILDS:
            try:
                setup(pob, cls, asc, items, gems)
            except Exception as e:  # noqa: BLE001
                print(f"{name}: setup failed: {e}")
                continue
            xml = pob.save_xml()
            rows = {}
            for label, kw in (("old", dict(far_dist=6, refine=False)), ("new", dict())):
                pob.load_xml(xml)
                t = time.time()
                res = pob.optimise_tree(metric=metric, **kw)
                secs = time.time() - t
                out = pob.calc(FIELDS)
                rows[label] = (score_of(out, metric), out.get("TotalEHP") or 0, secs, res)
            o, n = rows["old"], rows["new"]
            gain = (n[0] / o[0] - 1) * 100 if o[0] else 0
            print(f"{name}\n  old: score {o[0]:>12,.0f}  EHP {o[1]:>9,.0f}  {o[2]:5.1f}s")
            print(f"  new: score {n[0]:>12,.0f}  EHP {n[1]:>9,.0f}  {n[2]:5.1f}s   ({gain:+.1f}% damage)"
                  f"  swaps kept {len(n[3].get('swaps') or [])}/{n[3].get('swap_tries')}")
            for sw in n[3].get("swaps") or []:
                print(f"     took back {len(sw['removed'])} pts at {sw['name']}")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
