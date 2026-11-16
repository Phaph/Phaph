"""Trace base choice in the final gear pass of one stage: candidates, their scores and the attributes.

    python tools/debug_bases.py '<spec json>' leveling "Body Armour"
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import gear  # noqa: E402
from guide import build_stage  # noqa: E402

spec, stage_key, slot = json.loads(sys.argv[1]), sys.argv[2], sys.argv[3]
orig_best, orig_craft = gear._best_base, gear.craft_gear


def traced_best(pob, s, candidates, stage, score):
    pick = orig_best(pob, s, candidates, stage, score)
    if s == slot and score.attr_weight:
        ref = pob.calc(gear.SCORE_FIELDS)
        outs = gear._try(pob, s, [gear._item_raw("t", c["name"], [], gear.base_implicits(c, stage.roll) or ())
                                  for c in candidates])
        print("attrs", {k: ref.get(k) for k in ("Str", "Dex", "Int", "ReqStr", "ReqDex", "ReqInt")})
        for c, o in zip(candidates, outs):
            print(f"  {c['name']:<22} req {c.get('req')}  score {score(o, ref) if o else None:.3f}  "
                  f"deficit {gear._attr_deficit(o) if o else None}")
        print("  picked", pick)
    return pick


def traced_craft(*a, **k):
    plans = orig_craft(*a, **k)
    if k.get("attr_weight"):
        print("final pass", slot, [p.base for p in plans if p.slot == slot])
    return plans


gear._best_base = traced_best
gear.craft_gear = traced_craft
import guide  # noqa: E402
guide.craft_gear = traced_craft
g = build_stage(spec, stage_key)
print("in the guide:", [(p.slot, p.base, p.unique) for p in g.gear if p.slot == slot])
