"""Lodestone (code name: the Breaker): one plain summary of the committed Breaker results for the unlisted page
api/static/lodestone.html. Read from files only, no PoB calls: leads.json (curated), conditions.json, combos.json,
pairs.json, matrix.json, and the server queue's status line. Cached until a file changes."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "engine"))
BREAKER_DIR = Path(os.environ.get("BREAKER_DIR", str(ROOT / "engine" / "data" / "breaker")))
JOBS_DIR = Path(os.environ.get("SERVER_JOBS_DIR", "/server_jobs"))

_cache: dict = {"key": None, "data": None}


def _load(name: str) -> dict | None:
    try:
        return json.loads((BREAKER_DIR / name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _key() -> tuple:
    files = [BREAKER_DIR / n for n in ("leads.json", "conditions.json", "combos.json", "pairs.json", "matrix.json")]
    files += sorted(JOBS_DIR.glob("*.status")) if JOBS_DIR.exists() else []
    return tuple((str(f), f.stat().st_mtime) for f in files if f.exists())


def _cond_name(c: str) -> str:
    """'ArmourBroken' -> 'armour broken', 'OnShockedGround' -> 'on shocked ground'."""
    out = ""
    for ch in c:
        out += (" " + ch.lower()) if ch.isupper() and out else ch.lower()
    return out


def _payoffs(d: dict | None, n: int = 15) -> list[dict]:
    if not d:
        return []
    from condition_scan import payoffs
    return [{"skill": s, "condition": _cond_name(c), "gain": round(v, 3), "usual": round(v - x, 3)}
            for s, c, v, x in payoffs(d)[:n]]


def _combos(d: dict | None, n: int = 12) -> list[dict]:
    if not d:
        return []
    from combo_scan import combos
    keep = ("payoff", "setup", "swap", "alone", "dps", "edge", "gain", "gain_if_always", "time_to_break", "uptime")
    return [{k: r.get(k) for k in keep} for r in combos(d)[:n]]


def _pairs(n: int = 10) -> list[dict]:
    if not (BREAKER_DIR / "pairs.json").exists():
        return []
    from breaker import report
    keep = ("build", "a", "b", "gain_a", "gain_b", "gain_ab", "synergy")
    return [{k: r.get(k) for k in keep} for r in report(BREAKER_DIR / "pairs.json", n)]


def _interactions(d: dict | None, n: int = 15) -> dict:
    if not d:
        return {"one_skill": [], "broad": []}
    from matrix_scan import BROAD_SKILLS, family_outliers, strong_counts
    counts = strong_counts(d)
    # Skill types for the families (matrix_scan.py stores them since 2026-11-19; older files use skill_types.json).
    types = {n: set(t) for n, t in (_load("skill_types.json") or {}).items()} or None
    rows = [r for r in family_outliers(d, types) if counts.get(r[1], 0) <= BROAD_SKILLS]
    return {
        "one_skill": [{"skill": s, "piece": k.split(":", 1)[1], "kind": k.split(":")[0], "gain": round(v, 3),
                       "usual": round(v - x, 3), "peers": nf} for s, k, v, x, nf in rows[:n]],
        "broad": [{"piece": k.split(":", 1)[1], "kind": k.split(":")[0], "skills": c}
                  for k, c in sorted(counts.items(), key=lambda kv: -kv[1]) if c > BROAD_SKILLS][:10],
    }


def _queue() -> list[dict]:
    if not JOBS_DIR.exists():
        return []
    out = []
    for f in sorted(JOBS_DIR.glob("*.status")):
        try:
            out.append({"job": f.stem, "status": f.read_text(encoding="utf-8").strip()[:300]})
        except OSError:
            continue
    return out


def summary() -> dict:
    key = _key()
    if _cache["key"] == key and _cache["data"] is not None:
        return _cache["data"]
    leads = _load("leads.json") or {"leads": []}
    data = {
        "leads": leads.get("leads", []),
        "leads_updated": leads.get("updated"),
        "payoffs": _payoffs(_load("conditions.json")),
        "combos": _combos(_load("combos.json")),
        "pairs": _pairs(),
        "interactions": _interactions(_load("matrix.json")),
        "queue": _queue(),
    }
    _cache.update(key=key, data=data)
    return data
