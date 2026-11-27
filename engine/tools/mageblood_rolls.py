# Task 57: Mageblood best / median / worst roll on saved builds. Run in the image: python mageblood_rolls.py (paths /s/...).
# Mageblood on saved Uber builds: score of the best roll (current engine: best per slot, greedy) vs a typical roll
# (median per slot) vs the build's own belt. Bossing config. An estimate: no re-optimisation around the belt.
import sys, json, statistics; sys.path.insert(0, "/app/engine")
from pob import PoB
import gear
from gear import Scorer, SCORE_FIELDS, _set_variant, VARIANT_KEYS, HAS_ALT, _try
d = json.load(open("/s/rank_check_8.json"))
builds = [(a, s, v["code"]) for a, av in d["ascendancies"].items() for s, v in av["skills"].items() if v.get("code")]
sc = Scorer(mode="bossing")
done = set()
try:
    done = {json.loads(l)["build"] for l in open("/s/mb.out.done") if l.startswith("{")}
except Exception:
    pass
with PoB() as p0:
    mb = next(u for u in p0.list_uniques() if u["name"].startswith("Mageblood"))
    names = [ln[9:] for ln in mb["raw"].split("\n") if ln.startswith("Variant: ")]
    keys = ["Selected Variant"] + [k for k in VARIANT_KEYS[1:] if HAS_ALT[k] in mb["raw"]]
for asc, skill, code in builds:
    if f"{skill} {asc}" in done:
        continue
    try:
      with PoB() as p:
        p.load_code(code); p.set_config(enemyIsBoss="Pinnacle")
        own = p.calc(SCORE_FIELDS)
        res = {}
        for mode in ("best", "median", "worst"):
            raw = mb["raw"]; picks = []
            for key in keys:
                cands = [_set_variant(raw, key, i) for i in range(1, len(names) + 1)]
                outs = _try(p, "Belt", cands)
                scored = sorted((sc(o, own), i) for i, o in enumerate(outs) if o is not None)
                j = {"best": -1, "median": (len(scored) - 1) // 2, "worst": 0}[mode]
                raw = cands[scored[j][1]]; picks.append(names[scored[j][1]].replace("Legacy of ", ""))
            p.send("equip", slot="Belt", raw=raw, fields=SCORE_FIELDS)
            o = p.calc(SCORE_FIELDS)
            res[mode] = (round(sc(o, own), 3), round(gear.total_dps(o) / max(gear.total_dps(own), 1), 3), picks)
            p.load_code(code); p.set_config(enemyIsBoss="Pinnacle")
        print(json.dumps({"build": f"{skill} {asc}", **res}), flush=True)
    except Exception as e:
        print(json.dumps({"build": f"{skill} {asc}", "error": str(e)[:100]}), flush=True)
