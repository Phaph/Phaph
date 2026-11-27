# Task 57: Megalomaniac best vs typical (median per slot) roll, replacing the jewel in an allocated socket. Bossing.
import sys, json; sys.path.insert(0, "/app/engine")
from pob import PoB
import gear
from gear import Scorer, SCORE_FIELDS, _set_variant, VARIANT_KEYS, HAS_ALT, _try
d = json.load(open("/s/rank_check_8.json"))
pick = sys.argv[1].split(",")
builds = [(a, s, v["code"]) for a, av in d["ascendancies"].items() for s, v in av["skills"].items() if v.get("code") and f"{s} {a}" in pick]
sc = Scorer(mode="bossing")
for asc, skill, code in builds:
    with PoB() as p:
        u = next(x for x in p.list_uniques() if x["name"].startswith("Megalomaniac"))
        names = [ln[9:] for ln in u["raw"].split("\n") if ln.startswith("Variant: ")]
        keys = ["Selected Variant"] + [k for k in VARIANT_KEYS[1:] if HAS_ALT[k] in u["raw"]]
        p.load_code(code); p.set_config(enemyIsBoss="Pinnacle")
        socks = [s for s in p.send("jewel_sockets")["sockets"] if s["alloc"] and s["plain"] and s["has_slot"]]
        if not socks:
            print(json.dumps({"build": f"{skill} {asc}", "error": "no allocated jewel socket"}), flush=True); continue
        slot = socks[0]["slot"]
        own = p.calc(SCORE_FIELDS)
        res = {"socket": slot}
        for mode in ("best", "median"):
            raw = u["raw"]; picks = []
            for key in keys:
                cands = [_set_variant(raw, key, i) for i in range(1, len(names) + 1)]
                outs = _try(p, slot, cands)
                scored = sorted((sc(o, own), i) for i, o in enumerate(outs) if o is not None)
                j = -1 if mode == "best" else (len(scored) - 1) // 2
                raw = cands[scored[j][1]]; picks.append(names[scored[j][1]])
            p.send("equip", slot=slot, raw=raw, fields=SCORE_FIELDS)
            o = p.calc(SCORE_FIELDS)
            res[mode] = (round(sc(o, own), 3), round(gear.total_dps(o) / max(gear.total_dps(own), 1), 3), picks)
            p.load_code(code); p.set_config(enemyIsBoss="Pinnacle")
        print(json.dumps({"build": f"{skill} {asc}", **res}), flush=True)
