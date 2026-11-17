"""Theme -> generated build -> plan -> guide, printed as markdown. Slow (10-20 minutes).

  python3 tools/end_to_end.py '{"ailment":"bleed","kinds":["melee"]}' [--stages end]
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from generate import generate, options, plan_build  # noqa: E402
from guide import build_guide, to_markdown  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("request")
ap.add_argument("--stages", default="end")
a = ap.parse_args()
t = time.time()
res = generate(json.loads(a.request))
plan = plan_build(res)
print("\nPLAN:", json.dumps(plan, indent=2))
print("OPTIONS:", json.dumps(options(res), indent=2))
guides = build_guide(plan["spec"], a.stages.split(","), log=print)
print(to_markdown(plan["spec"], guides))
print(f"\nTotal {time.time() - t:.0f}s")
