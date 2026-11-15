"""Check Whetstone's Cast on Critical estimate against the real game.

1. In game, set up Cast on Critical with one spell (e.g. Comet), fed by an attack that crits.
2. Export the character to Path of Building (or copy its PoB code from poe.ninja) and save the code in a file.
3. Run:  python engine/tools/trigger_check.py my_build.txt --gem-level 20
4. It prints how often the spell should fire. Count it in game (record 30 seconds of steady attacking and count
   the casts, once on a pack of white monsters and once on a boss), then send both counts back.

The numbers it uses that aren't Path of Building's live in engine/data/trigger_rules.json.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from optimize import MODE_CONFIG  # noqa: E402
from pob import PoB  # noqa: E402
from triggers import cast_on_crit, find_groups, load_rules  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("code_file", help="file holding the character's Path of Building code")
    ap.add_argument("--gem-level", type=int, default=20, help="level of the Cast on Critical gem")
    ap.add_argument("--attack-group", type=int, help="socket group number of the attack (default: the main skill)")
    args = ap.parse_args()
    code = Path(args.code_file).read_text(encoding="utf-8").strip()
    rules = load_rules()
    with PoB() as pob:
        pob.load_code(code)
        coc, others = find_groups(pob)
        if not coc:
            sys.exit("No Cast on Critical gem found in this build.")
        main_group = next((g["group"] for g in pob.send("groups")["groups"] if g["main"]), None)
        attack = args.attack_group or (main_group if main_group != coc else others[0])
        for mode, where in (("mapping", "a pack of white monsters"), ("bossing", "a single boss")):
            pob.set_config(**MODE_CONFIG[mode])
            e = cast_on_crit(pob, attack, coc, mode=mode, gem_level=args.gem_level, rules=rules)
            a, en = e["attack"], e["energy"]
            if a["crit_chance"] <= 0:
                print("\nThis attack can't crit (a keystone or support stops crits), so Cast on Critical never fires.")
            print(f"\n== Against {where} ==")
            print(f"Attack: {a['hits_per_sec']:.2f} hits/s, {a['crit_chance']:.1%} crit -> {a['crits_per_sec']:.2f} crits/s,"
                  f" average crit {a['crit_hit']:,.0f}")
            ratio = f"{en['threshold_ratio']:.2f}" + (f" (crit {a['crit_hit']:,.0f} / threshold {en['enemy_threshold']:,.0f})"
                                                     if en["enemy_threshold"] else " (assumed for map monsters)")
            print(f"Energy: power {en['monster_power']} x ratio {ratio} -> {en['per_crit']:.2f} per crit;"
                  f" {en['to_fire']:.0f} to fire")
            for s in e["spells"]:
                n30 = s["casts_per_sec"] * 30
                print(f"  {s['spell']}: about {s['casts_per_sec']:.2f} casts/s -> ~{n30:.0f} casts in 30 seconds"
                      + (f" (cooldown {s['cooldown']}s)" if s["cooldown"] else "")
                      + f", {s['damage_per_cast']:,.0f} damage per cast")
            print(f"Trigger DPS {e['trigger_dps']:,.0f} + attack {a['dps']:,.0f} = {e['total_dps']:,.0f}"
                  f"  ({'checked in game' if e['verified'] else 'estimate, not yet checked in game'})")


if __name__ == "__main__":
    main()
