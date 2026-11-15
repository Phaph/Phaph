"""Evaluate one generate candidate and print why it fails (or its numbers).

    python tools/debug_candidate.py '{"ailment":"bleed","weapons":["Crossbow"],"goals":["crit"]}' "Armour Piercing Rounds" Mercenary
"""
import json
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import generate  # noqa: E402
from gear import make_stage  # noqa: E402
from pob import PoB  # noqa: E402

req = json.loads(sys.argv[1])
skill, cls = sys.argv[2], sys.argv[3]
asc = sys.argv[4] if len(sys.argv) > 4 else None
with PoB() as p:
    catalog = p.send("skill_catalog")["skills"]
s = next(x for x in catalog if x["name"] == skill)
print("weapons:", generate.weapon_options(s, req))
print("main_skills has it:", any(m["name"] == skill for m in generate.main_skills(catalog, req)))
wt, ws, off = generate.weapon_options(s, req)[0]
c = generate.Candidate(skill, wt, ws, off, cls, asc)
stage = make_stage("end", req.get("budget", "high"))
try:
    generate.evaluate(c, stage, req, tree="--tree" in sys.argv)
except Exception:
    traceback.print_exc()
print({k: v for k, v in c.__dict__.items()})
