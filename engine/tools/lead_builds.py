"""Leads to full builds (Breaker roadmap, task 16): each Lodestone lead with a `build` entry becomes a full Whetstone
stage guide built around its pieces, saved with its PoB code, so a lead comes with a complete build.

A lead's `build` (engine/data/breaker/leads.json):
    {"job": "<job id of the build the lead was found on>", "anchor_unique": "...", "anchor_support": "...",
     "anchor_keystone": "...", "stages": ["end"]}
The job's spec (class, ascendancy, skill, weapon) comes from the site's job database; the anchors make the guide
wear the unique / take the keystone / keep the support at every stage that can (anchors.py). The saved job's own
stage was the first baseline, but it ran on an older engine: each lead is also built without its pieces on today's
engine (baseline.now), and the report compares with that.

  python tools/lead_builds.py run --jobs /data/jobs.sqlite3 [--out data/breaker/lead_builds] [--only "Leopold"]
  python tools/lead_builds.py report data/breaker/lead_builds
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
import time
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE))
LEADS = ENGINE / "data" / "breaker" / "leads.json"
OUT = ENGINE / "data" / "breaker" / "lead_builds"


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")[:60]


def run(db: str, out: Path, only: str | None) -> None:
    from guide import build_stage
    out.mkdir(parents=True, exist_ok=True)
    leads = [l for l in json.loads(LEADS.read_text(encoding="utf-8"))["leads"] if l.get("build")]
    if only:
        leads = [l for l in leads if only.lower() in l["name"].lower()]
    con = sqlite3.connect(db)
    for lead in leads:
        b = lead["build"]
        path = out / f"{slug(lead['name'])}.json"
        if path.exists():
            rec = json.loads(path.read_text(encoding="utf-8"))
            if all("now" in (s.get("baseline") or {}) or s.get("error") for s in rec["stages"].values()):
                continue
            plain = {k: v for k, v in rec["spec"].items() if not k.startswith("anchor_")}
            for key, s in rec["stages"].items():
                if s.get("error") or "now" in s["baseline"]:
                    continue
                g = build_stage(plain, key)   # the same build without the pieces, on today's engine
                s["baseline"]["now"] = {"dps": round(g.dps), "boss_dps": round(g.boss_dps)}
                print(f"{lead['name']} [{key}] baseline now: {g.boss_dps:,.0f}", flush=True)
            path.write_text(json.dumps(rec, indent=1, ensure_ascii=False), encoding="utf-8")
            continue
        row = con.execute("select result from jobs where id=?", (b["job"],)).fetchone()
        if not row:
            print(f"{lead['name']}: job {b['job']} not in the database", flush=True)
            continue
        job = json.loads(row[0])
        spec = {**job["spec"], **{k: b[k] for k in ("anchor_unique", "anchor_support", "anchor_keystone") if b.get(k)}}
        rec = {"lead": lead["name"], "spec": spec, "stages": {}}
        for key in b.get("stages") or ["end"]:
            t0 = time.time()
            base = next((s for s in job["stages"] if s.get("stage") == key), {})
            try:
                g = build_stage(spec, key)
                plain = {k: v for k, v in spec.items() if not k.startswith("anchor_")}
                g0 = build_stage(plain, key)   # the same build without the pieces, on today's engine
                rec["stages"][key] = {"dps": round(g.dps), "boss_dps": round(g.boss_dps), "code": g.code,
                                      "supports": g.supports, "notes": g.notes,
                                      "baseline": {"dps": round(base.get("dps") or 0),
                                                   "boss_dps": round(base.get("boss_dps") or 0),
                                                   "now": {"dps": round(g0.dps), "boss_dps": round(g0.boss_dps)}},
                                      "seconds": round(time.time() - t0)}
            except Exception as e:  # noqa: BLE001 - one lead must not stop the rest
                rec["stages"][key] = {"error": f"{type(e).__name__}: {e}"}
            print(f"{lead['name']} [{key}]: {rec['stages'][key].get('error') or rec['stages'][key]['boss_dps']}", flush=True)
        rec["updated"] = time.strftime("%Y-%m-%d %H:%M")
        path.write_text(json.dumps(rec, indent=1, ensure_ascii=False), encoding="utf-8")


def report(out: Path) -> str:
    lines = ["Lead builds (full Whetstone stage guides built around each lead's pieces):"]
    for p in sorted(out.glob("*.json")):
        r = json.loads(p.read_text(encoding="utf-8"))
        for key, s in r["stages"].items():
            if s.get("error"):
                lines.append(f"  {r['lead']} [{key}]: {s['error']}")
                continue
            now = (s["baseline"].get("now") or {}).get("boss_dps")
            base = now or s["baseline"]["boss_dps"]
            gain = s["boss_dps"] / base - 1 if base else 0
            when = "today's engine" if now else "the saved job, an older engine"
            lines.append(f"  {r['lead']} [{key}]: boss {s['boss_dps']:,} vs {base:,} without the pieces ({when}: {gain:+.0%}); "
                         f"mapping {s['dps']:,}; supports {', '.join(s['supports'])}")
    return "\n".join(lines)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "run":
        run(a[a.index("--jobs") + 1], Path(a[a.index("--out") + 1]) if "--out" in a else OUT,
            a[a.index("--only") + 1] if "--only" in a else None)
    elif a and a[0] == "report":
        print(report(Path(a[1]) if len(a) > 1 else OUT))
    else:
        print(__doc__)
