"""Build a prompt end to end and show whether the result delivers what was asked (theme share, focus stats).

    python tools/check_prompt.py "crossbow crit bleed build" [stage]
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate import generate, plan_build  # noqa: E402
from goals import FOCUS, focus_value  # noqa: E402
from guide import build_guide  # noqa: E402
from optimize import AILMENT_FIELD, ailment_dps, total_dps  # noqa: E402
from pob import PoB  # noqa: E402
from prompt import parse_prompt  # noqa: E402

text = sys.argv[1]
stage = sys.argv[2] if len(sys.argv) > 2 else "end"
with PoB() as p:
    cat = p.send("skill_catalog")["skills"]
    classes = p.list_classes()
catalog = {"skills": [s["name"] for s in cat], "classes": classes, "weapon_types": {},
           "helper_skills": [s["name"] for s in cat if set(s["types"]) & {"Buff", "Aura", "Herald", "Meta"}]}
parsed = parse_prompt(text, catalog)
req = {"budget": "high", **parsed["request"]}
print("read as:", [f["means"] for f in parsed["found"]], "unused:", parsed["unused"])
t0 = time.time()
result = generate(req, workers=int(os.environ.get("WORKERS", "3")), log=lambda *a: None)
print("relaxed:", result.get("relaxed"))
plan = plan_build(result)
spec = {**plan["spec"], "budget": req["budget"]}
print("picked:", spec["skill"], spec["ascendancy"], spec["weapon_type"], f"({time.time() - t0:.0f}s)")
g = build_guide(spec, [stage], log=lambda *a: None)[0]
s = g.stats
for setup in g.setups[:3]:
    print("  ", setup.get("skill"), "+", ", ".join(setup.get("supports") or []))
if req.get("ailment") in AILMENT_FIELD:
    print(f"{req['ailment']} share: {ailment_dps(s, req['ailment']) / max(total_dps(s), 1):.0%}")
for k in req.get("goals") or []:
    if k in FOCUS:
        print(f"{FOCUS[k][2]}: {focus_value(s, k):,.1f}  (target {FOCUS[k][3]})")
print("total dps:", f"{total_dps(s):,.0f}")
print("notes:", [n for n in g.notes if n.startswith("Off theme")])
