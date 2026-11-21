"""Trigger detector (b): which attacks feed each meta gem fastest (Breaker roadmap week 2, task 15).

For every melee attack the search can pick, on crafted mid-game gear for its weapon (crafted once per weapon type,
then each attack swapped in), with no supports of its own: the energy per second it gives a meta gem against a
pinnacle boss and on maps (triggers.cast_on_crit: hits x crit (Cast on Critical) or every hit (Thundergod's Wrath,
Fire Spell on Melee Hit) x monster power x the hit's share of the enemy's ailment threshold), and how often that
fires a reference spell. A lead is a feeder that fires the spell >= 1 time a second against a boss: the trigger
deals real boss damage on top of the attack.

  python tools/trigger_scan.py run [--out data/breaker/triggers.json] [--only Boneshatter,Sunder]   (resumable)
  python tools/trigger_scan.py report data/breaker/triggers.json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE))
OUT = ENGINE / "data" / "breaker" / "triggers.json"
METAS = [("Cast on Critical", "Arc"), ("Thundergod's Wrath", "Arc"), ("Fire Spell on Melee Hit", "Fireball")]
CLASS_FOR = {"One Hand Mace": "Warrior", "Two Hand Mace": "Warrior", "Spear": "Huntress", "Quarterstaff": "Monk",
             "Talisman": "Druid", "Claw": "Monk", "Dagger": "Monk", "One Hand Sword": "Warrior",
             "Two Hand Sword": "Warrior", "One Hand Axe": "Warrior", "Two Hand Axe": "Warrior", "Flail": "Warrior"}
LEAD_CASTS = 1.0


def run(out: Path, only: set[str] | None) -> None:
    from gear import craft_gear, make_stage
    from generate import main_skills, weapon_key, weapon_options
    from optimize import MODE_CONFIG
    from pob import PoB
    from triggers import cast_on_crit

    st = make_stage("mid")
    done = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {"rows": {}}
    with PoB() as p:
        cat = p.send("skill_catalog")["skills"]
        melee = [s for s in main_skills(cat, {}) if {"Attack", "Melee"} <= set(s["types"])
                 and "Minion" not in s["types"] and (not only or s["name"] in only)]
        by_weapon: dict[tuple, list[str]] = {}
        for s in melee:
            opts = weapon_options(s, {})
            if opts:
                by_weapon.setdefault(opts[0], []).append(s["name"])
        print(f"{len(melee)} melee attacks on {len(by_weapon)} weapons", flush=True)
        for (wtype, wsub, off), names in by_weapon.items():
            todo = [n for n in names if n not in done["rows"]]
            if not todo:
                continue
            key = weapon_key(wtype, wsub)
            p.new()
            p.set_class(CLASS_FOR.get(key, "Warrior"), None)
            p.set_level(st.level)
            a = p.add_skill([todo[0]])["group"]
            p.set_config(**MODE_CONFIG["bossing"])
            craft_gear(p, st, wtype, wsub, offhand_type=off, uniques=False, metric="TotalDPS", log=lambda *x: None)
            groups = {}
            for gem, spell in METAS:
                groups[gem] = p.add_skill([gem, spell], main=False)["group"]
            for name in todo:
                t0 = time.time()
                row = {"weapon": key, "metas": {}}
                try:
                    p.try_skill(a, [name], ["TotalDPS"])
                    p.send("set_main", group=a)
                    for mode in ("bossing", "mapping"):
                        p.set_config(**MODE_CONFIG[mode])
                        p.auto_config(mode)
                        for gem, spell in METAS:
                            r = cast_on_crit(p, a, groups[gem], mode=mode, gem=gem)
                            m = row["metas"].setdefault(gem, {"spell": spell})
                            m[mode] = {"hits_per_sec": round(r["attack"]["hits_per_sec"], 3),
                                       "energy_per_sec": round(r["attack"]["crits_per_sec"] * r["energy"]["per_crit"], 2),
                                       "threshold_ratio": round(r["energy"]["threshold_ratio"] or 0, 4),
                                       "casts_per_sec": round(r["casts_per_sec"], 3),
                                       "attack_dps": round(r["attack"]["dps"]), "trigger_dps": round(r["trigger_dps"])}
                except Exception as e:  # noqa: BLE001 - one attack must not stop the scan
                    row["error"] = f"{type(e).__name__}: {e}"
                row["seconds"] = round(time.time() - t0, 1)
                done["rows"][name] = row
                done["updated"] = time.strftime("%Y-%m-%d %H:%M")
                out.write_text(json.dumps(done, indent=1, ensure_ascii=False), encoding="utf-8")
                print(f"  {name:<26} {row.get('error') or ''}", flush=True)
    print(report(done), flush=True)


def report(d: dict, top: int = 12) -> str:
    lines = [f"Trigger feeders: {len(d['rows'])} melee attacks, mid-game gear, no supports (updated {d.get('updated')})."]
    for gem, spell in METAS:
        rows = [(n, r["metas"][gem]) for n, r in d["rows"].items() if gem in (r.get("metas") or {})]
        for mode in ("bossing", "mapping"):
            rows.sort(key=lambda x: -(x[1].get(mode) or {}).get("energy_per_sec", 0))
            lines.append(f"\n{gem} -> {spell}, {mode}: best feeders (energy/s, casts/s, threshold ratio, trigger vs attack)")
            for n, m in rows[:top]:
                x = m.get(mode) or {}
                flag = "  LEAD" if mode == "bossing" and x.get("casts_per_sec", 0) >= LEAD_CASTS else ""
                share = x.get("trigger_dps", 0) / max(x.get("attack_dps", 1), 1)
                lines.append(f"  {n:<26} {x.get('energy_per_sec', 0):>8.1f} {x.get('casts_per_sec', 0):>6.2f}/s "
                             f"ratio {x.get('threshold_ratio', 0):.3f}  trigger {share:+.0%} of the attack{flag}")
    errs = [n for n, r in d["rows"].items() if r.get("error")]
    if errs:
        lines.append(f"\n{len(errs)} attacks errored: {', '.join(errs[:10])}")
    return "\n".join(lines)


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "run":
        out = Path(args[args.index("--out") + 1]) if "--out" in args else OUT
        only = set(args[args.index("--only") + 1].split(",")) if "--only" in args else None
        run(out, only)
    elif args and args[0] == "report":
        print(report(json.loads(Path(args[1] if len(args) > 1 else OUT).read_text(encoding="utf-8"))))
    else:
        print(__doc__)
