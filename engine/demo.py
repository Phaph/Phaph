"""Demo: find the best support gems for a skill on a simple test character.

Example:
  python3 demo.py --class Monk --ascendancy Invoker --skill "Tempest Flurry" \
    --item "$(printf 'Rarity: Rare\nTest Staff\nWyrm Quarterstaff\nAdds 20 to 300 Lightning Damage\n25%% increased Attack Speed')"
"""
import argparse

from optimize import optimise_supports
from pob import PoB


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--class", dest="cls", required=True)
    ap.add_argument("--ascendancy")
    ap.add_argument("--level", type=int, default=90)
    ap.add_argument("--skill", required=True)
    ap.add_argument("--item", action="append", default=[], help="item in PoB text format; repeatable")
    ap.add_argument("--slots", type=int, default=5)
    ap.add_argument("--metric", default="combined", help="hit, combined, or any PoB output field")
    ap.add_argument("--code", help="start from an existing PoB build code instead")
    args = ap.parse_args()

    with PoB() as pob:
        if args.code:
            pob.load_code(args.code)
        else:
            pob.new()
            pob.set_class(args.cls, args.ascendancy)
            pob.set_level(args.level)
            for raw in args.item:
                pob.add_item(raw)
        res = pob.add_skill([args.skill])
        if res["unknown_gems"]:
            raise SystemExit(f"Unknown skill: {args.skill}")
        best = optimise_supports(pob, res["group"], args.skill, slots=args.slots, metric=args.metric)[0]
        print("\nBest setup:", " + ".join([args.skill, *best.supports]))
        print("PoB code:", pob.save_code())


if __name__ == "__main__":
    main()
