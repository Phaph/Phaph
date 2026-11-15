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

_CATALOG: dict | None = None


def catalog() -> dict:
    global _CATALOG
    if _CATALOG is None:
        with PoB() as p:
            cat = p.send("skill_catalog")["skills"]
            classes = p.list_classes()
        _CATALOG = {"skills": [s["name"] for s in cat], "classes": classes, "weapon_types": {},
                    "helper_skills": [s["name"] for s in cat if set(s["types"]) & {"Buff", "Aura", "Herald", "Meta"}]}
    return _CATALOG


def check(text: str, stage: str = "end", budget: str = "high", workers: int = 3) -> dict:
    """Everything that says whether the build is what the prompt asked for, as plain data."""
    parsed = parse_prompt(text, catalog())
    req = {"budget": budget, **parsed["request"]}
    out = {"prompt": text, "read_as": [f["means"] for f in parsed["found"]], "unused": parsed["unused"]}
    t0 = time.time()
    try:
        result = generate(req, workers=workers, log=lambda *a: None)
        plan = plan_build(result)
    except Exception as e:  # noqa: BLE001
        return {**out, "error": f"generate: {e}"}
    spec = {**plan["spec"], "budget": req["budget"]}
    out.update(relaxed=result.get("relaxed") or [], skill=spec["skill"], ascendancy=spec["ascendancy"],
               weapon=spec["weapon_type"])
    try:
        g = build_guide(spec, [stage], log=lambda *a: None)[0]
    except Exception as e:  # noqa: BLE001
        return {**out, "error": f"guide: {e}"}
    s = g.stats
    out["seconds"] = round(time.time() - t0)
    out["setups"] = [f'{x.get("skill")} + {", ".join(x.get("supports") or [])}' for x in g.setups[:4]]
    if req.get("ailment") in AILMENT_FIELD:
        out["ailment"] = req["ailment"]
        out["ailment_share"] = round(ailment_dps(s, req["ailment"]) / max(total_dps(s), 1), 3)
    out["focus"] = {k: {"value": round(focus_value(s, k), 1), "target": FOCUS[k][3]}
                    for k in req.get("goals") or [] if k in FOCUS}
    out["total_dps"] = round(total_dps(s))
    out["off_theme"] = [n for n in g.notes if n.startswith("Off theme")]
    return out


def show(r: dict) -> None:
    print("read as:", r["read_as"], "unused:", r["unused"])
    if r.get("error"):
        print("ERROR", r["error"])
        return
    print("relaxed:", r["relaxed"])
    print("picked:", r["skill"], r["ascendancy"], r["weapon"], f"({r['seconds']}s)")
    for line in r["setups"]:
        print("  ", line)
    if "ailment_share" in r:
        print(f"{r['ailment']} share: {r['ailment_share']:.0%}")
    for k, v in r["focus"].items():
        print(f"{FOCUS[k][2]}: {v['value']:,.1f}  (target {v['target']})")
    print("total dps:", f"{r['total_dps']:,}")
    print("notes:", r["off_theme"])


if __name__ == "__main__":
    show(check(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "end",
               workers=int(os.environ.get("WORKERS", "3"))))
