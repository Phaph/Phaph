"""Baseline prompts: run a fixed set of prompts end to end, save the results, and compare two runs.

    python tools/baseline.py run [out.json]          # default: data/baseline/prompts_<PoB version>.json
    python tools/baseline.py compare old.json new.json

Run it on the old PoB before an update and on the new one after (LAUNCH_1.0.md). The compare flags what matters to
a player: an error or no build, a request that didn't make it into the build (ailment share under its target, a stat
focus under its minimum, relaxed choices, off-theme notes, words not understood), and big DPS changes. Reworks
make DPS move, so DPS changes are listed for review, not as failures.
Takes about 10 minutes a prompt (WORKERS=3).
"""
import json
import os
import re
import sys
import time
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS.parent))
sys.path.insert(0, str(TOOLS))

from check_prompt import check  # noqa: E402
from optimize import AILMENT_TARGET  # noqa: E402

# What players ask for, across themes, weapons, focuses and helpers. Keep it fixed so runs compare.
PROMPTS = [
    "crossbow crit bleed build",
    "lightning minion build",
    "dagger bleed build",
    "cast on crit fire spells",
    "poison bow build",
    "tanky ignite build",
    "cold spell build",
    "two hand mace slam warrior",
    "spear attack speed build",
    "chaos damage over time witch",
    "warcry build",
    "block energy shield build",
    "lightning arrow with heralds",
    "minion build for a new player",
    "highest dps build possible",
]


def run(out_path: Path | None) -> None:
    from pob import PoB
    with PoB() as p:
        version = p.version
    out_path = out_path or TOOLS.parent / "data" / "baseline" / f"prompts_{version}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done = json.loads(out_path.read_text(encoding="utf-8")) if out_path.exists() else {}
    if done.get("pob_version") != version:
        done = {"pob_version": version, "results": {}}
    for text in PROMPTS:
        key = text
        if key in done["results"]:
            continue   # resumes where it stopped
        print(f"{key} ...", flush=True)
        r = check(text, "end", workers=int(os.environ.get("WORKERS", "3")))
        done["results"][key] = r
        done["updated"] = time.strftime("%Y-%m-%d %H:%M")
        out_path.write_text(json.dumps(done, indent=1, ensure_ascii=False), encoding="utf-8")
        print("   ", problems(r) or "ok", "|", r.get("skill"), r.get("ascendancy"), f"{r.get('total_dps', 0):,}",
              flush=True)
    print("saved", out_path)


def problems(r: dict) -> list[str]:
    """Ways the build fails to be what was asked for."""
    if r.get("error"):
        return [r["error"]]
    out = []
    if r.get("ailment_share") is not None and r["ailment_share"] < AILMENT_TARGET:
        out.append(f"{r['ailment']} only {r['ailment_share']:.0%} of damage")
    for k, v in (r.get("focus") or {}).items():
        if v["target"] and v["value"] < v["target"]:
            out.append(f"{k} {v['value']} under {v['target']}")
    if r.get("relaxed"):
        out.append(f"relaxed: {r['relaxed']}")
    if r.get("off_theme"):
        out.append("off theme")
    if r.get("unused"):
        out.append(f"words not understood: {r['unused']}")
    if not r.get("total_dps"):
        out.append("no damage")
    return out


def compare(old_path: Path, new_path: Path) -> int:
    old, new = (json.loads(p.read_text(encoding="utf-8")) for p in (old_path, new_path))
    print(f"PoB {old['pob_version']} -> {new['pob_version']}")
    failed = 0
    # Runs from before 2026-11-18 keyed prompts as "text [budget]"; there is no budget now.
    for run in (old, new):
        run["results"] = {re.sub(r" \[\w+\]$", "", k): v for k, v in run["results"].items()}
    for key in new["results"]:
        a, b = old["results"].get(key), new["results"][key]
        bad = problems(b)
        failed += bool(bad)
        line = f"{'FAIL' if bad else 'ok  '} {key}: {b.get('skill')} {b.get('ascendancy')}"
        if a and not a.get("error") and not b.get("error"):
            if (a["skill"], a["ascendancy"]) != (b["skill"], b["ascendancy"]):
                line += f" (was {a['skill']} {a['ascendancy']})"
            ratio = b["total_dps"] / max(a["total_dps"], 1)
            if ratio < 0.67 or ratio > 1.5:
                line += f", DPS {a['total_dps']:,} -> {b['total_dps']:,} ({ratio:.2f}x)"
        print(line)
        for p in bad:
            print("      ", p)
    missing = set(old["results"]) - set(new["results"])
    if missing:
        print("not run yet:", sorted(missing))
    print(f"{failed} of {len(new['results'])} prompts don't deliver what was asked")
    return 1 if failed else 0


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "run":
        run(Path(sys.argv[2]) if len(sys.argv) > 2 else None)
    elif len(sys.argv) == 4 and sys.argv[1] == "compare":
        sys.exit(compare(Path(sys.argv[2]), Path(sys.argv[3])))
    else:
        print(__doc__)
