"""Debug a theme that returns no build: which skills match, and why each candidate scored nothing.

    docker run --rm -i poe2-optimizer python engine/tools/why_empty.py < request.json
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generate import Candidate, DEFAULT_CLASS, evaluate, main_skills, weapon_options  # noqa: E402
from gear import make_stage  # noqa: E402
from pob import PoB  # noqa: E402

req = json.load(sys.stdin)
with PoB() as p:
    catalog = p.send("skill_catalog")["skills"]
skills = main_skills(catalog, req)
print(f"{len(skills)} skills match: {[s['name'] for s in skills]}")
stage = make_stage("mid", req.get("budget", "high"))
for s in skills:
    cls = req.get("class") or DEFAULT_CLASS.get("Minion" if "Minion" in s["types"] else "Spell", "Mercenary")
    for wt, ws, off in weapon_options(s, req):
        c = evaluate(Candidate(s["name"], wt, ws, off, cls, is_minion="Minion" in s["types"]), stage, req, tree=False)
        print(f"  {s['name']:<28} {wt:<10} score={c.score:>12,.0f} dps={c.dps:>12,.0f} error={c.error}")
