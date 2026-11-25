"""Condition scan: how much each damage skill gains when the enemy is in each state Path of Building can model.

Step 1 of the combo finder (PC_TODO "Mapping vs bossing"). Every skill that can be a main skill is built the quick way
the search builds round-1 candidates (gear and supports, no passive tree), then each enemy condition PoB offers
("Is the enemy Frozen / Cursed / Shocked / Armour Broken...", ~55 of them) is switched on alone and the damage measured.
A big jump means the skill is a payoff: it wants another skill to set that state up. For the Breaker, a jump far out of
line with the rest is a lead (a condition that multiplies instead of adds).

Conditions the build already assumes (auto_config: things it keeps up itself) read as no gain, so a gain here is
something the skill needs from elsewhere.

  python condition_scan.py run [--workers 6] [--out data/breaker/conditions.json]   (resumable)
  python condition_scan.py run --class Ranger --ascendancy Deadeye --out ...   (that class's weapons and ascendancy)
  python condition_scan.py report data/breaker/conditions.json
  python condition_scan.py diff OLD.json NEW.json   (damage per skill; launch day: what the patch moved)
  python condition_scan.py stamp   (the engine code this would scan with)
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ENGINE = Path(__file__).resolve().parent
OUT = ENGINE / "data" / "breaker" / "conditions.json"
MIN_GAIN = 0.05   # record conditions worth at least +5%


def conditions(pob_src: Path) -> list[str]:
    text = (pob_src / "Modules" / "ConfigOptions.lua").read_text(encoding="utf-8", errors="ignore")
    return sorted(set(re.findall(r'var = "(conditionEnemy[A-Za-z]+)"', text)) - {"conditionEnemyRareOrUnique"})


def code_stamp() -> str:
    """Hash of the engine code. Two scans compare the game only if this is the same; otherwise the diff is ours."""
    h = hashlib.sha256()
    for f in sorted(ENGINE.glob("*.py")) + [ENGINE / "runner.lua"]:
        h.update(f.name.encode() + f.read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()[:12]


def run(workers: int, out: Path, cls: str | None = None, asc: str | None = None) -> None:
    import generate as g
    from gear import make_stage
    from optimize import total_dps
    from pob import POB_SRC, PoB

    conds = conditions(POB_SRC)
    with PoB() as p:
        catalog = p.send("skill_catalog")["skills"]
        classes = p.list_classes()
        pob_version = getattr(p, "version", None)
    g._ALL_ASCS[:] = [(c["name"], a) for c in classes for a in c["ascendancies"]]
    skills = g.main_skills(catalog, {})
    done = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {"code": code_stamp(), "pob": pob_version, "skills": {}}
    todo = [s for s in skills if s["name"] not in done["skills"]]
    print(f"{len(skills)} skills, {len(todo)} to scan, {len(conds)} conditions, {workers} workers", flush=True)
    stage = make_stage("mid")
    lock = threading.Lock()

    def one(s):
        opts = g.weapon_options(s, {})
        # Lodestone has no class-weapon rule (Kyle 2026-11-22: that rule is Whetstone's, for guides that suit the
        # class; to find broken builds any class may use any weapon, e.g. a Gemling Spark build).
        w, sub, off = (opts or [(None, None, None)])[0]
        c = g.Candidate(s["name"], w, sub, off, cls or g.DEFAULT_CLASS.get("Minion" if "Minion" in s["types"] else
                        "Spell" if "Spell" in s["types"] else "", "Mercenary"), asc, is_minion="Minion" in s["types"],
                        totem=s.get("totem"))
        c = g.evaluate(c, stage, {}, tree=False)
        asc_nodes = []
        if asc and not c.error:
            from breaker import ascendancy_passives
            asc_nodes = ascendancy_passives(g._pob(), stage)
        rec = {"weapon": g.weapon_key(w, sub), "class": c.cls, "error": c.error, "gains": {}}
        if asc_nodes:
            rec["ascendancy_nodes"] = asc_nodes
        if not c.error:
            p = g._pob()
            try:
                base = total_dps(p.calc(g.FIELDS))
                rec["dps"] = round(base)
                if base > 0:
                    for cond in conds:
                        p.set_config(**{cond: True})
                        gain = total_dps(p.calc(g.FIELDS)) / base - 1
                        p.set_config(**{cond: False})
                        if gain >= MIN_GAIN:
                            rec["gains"][cond.removeprefix("conditionEnemy")] = round(gain, 3)
            except Exception as e:  # noqa: BLE001 - one skill must not stop the scan
                rec["error"] = f"{type(e).__name__}: {e}"
        with lock:
            done["skills"][s["name"]] = rec
            done["updated"] = time.strftime("%Y-%m-%d %H:%M")
            out.write_text(json.dumps(done, indent=1, ensure_ascii=False), encoding="utf-8")
        top = sorted(rec["gains"].items(), key=lambda kv: -kv[1])[:3]
        print(f"  {s['name']:<28} {rec.get('dps', 0):>10,}  " + ", ".join(f"{k} +{v:.0%}" for k, v in top), flush=True)

    mine: list = []
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        with ThreadPoolExecutor(workers, initializer=g._bind, initargs=(mine,)) as pool:
            list(pool.map(one, todo))
    finally:
        g._close_all(mine)
    print(report(done), flush=True)


def payoffs(d: dict, margin: float = 0.15) -> list[tuple[str, str, float, float]]:
    """(skill, condition, gain, gain above the usual) for gains well above what that condition gives every skill.
    Shocked is +20% for nearly everything (more damage taken): that's a general boost, not a combo. A skill that gains
    far more than the usual from one condition is built to cash it in: a payoff, the other half of a combo."""
    by_cond: dict[str, list[float]] = {}
    n_ok = sum(1 for r in d["skills"].values() if not r.get("error"))
    for r in d["skills"].values():
        for c, v in (r.get("gains") or {}).items():
            by_cond.setdefault(c, []).append(v)
    usual = {}
    for c, vals in by_cond.items():
        vals = sorted(vals + [0.0] * max(n_ok - len(vals), 0))   # skills under +5% count as no gain
        usual[c] = vals[len(vals) // 2]
    out = [(n, c, v, v - usual[c]) for n, r in d["skills"].items() for c, v in (r.get("gains") or {}).items()
           if v - usual[c] >= margin]
    return sorted(out, key=lambda x: -x[3])


def report(d: dict, top: int = 30) -> str:
    rows = [(n, c, v) for n, r in d["skills"].items() for c, v in (r.get("gains") or {}).items()]
    rows.sort(key=lambda r: -r[2])
    by_cond: dict[str, list] = {}
    for n, c, v in rows:
        by_cond.setdefault(c, []).append((n, v))
    out = [f"{len(d['skills'])} skills scanned; {len(rows)} skill x condition gains of {MIN_GAIN:.0%}+",
           "Payoffs (gain well above what that condition gives every skill): combo halves, and Breaker leads if huge:"]
    out += [f"  +{v:>6.0%} (+{x:.0%} above usual)  {n:<28} when enemy is {c}" for n, c, v, x in payoffs(d)[:top]]
    out.append("Conditions that matter to the most skills:")
    for c, lst in sorted(by_cond.items(), key=lambda kv: -len(kv[1]))[:15]:
        out.append(f"  {c:<26} {len(lst):>3} skills, best: " + ", ".join(f"{n} +{v:.0%}" for n, v in sorted(lst, key=lambda x: -x[1])[:3]))
    return "\n".join(out)


def diff(old: dict, new: dict, margin: float = 0.05) -> str:
    """Skills whose damage moved, biggest first: a patch's number changes show here (the text diff reads wording only)."""
    a, b = old["skills"], new["skills"]
    out = []
    if not old.get("code") or old.get("code") != new.get("code"):
        out.append("WARNING: scanned with different engine code: some or all of these moves are ours, not the game's")
    if old.get("pob") != new.get("pob"):
        out.append(f"PoB {old.get('pob')} -> {new.get('pob')}")
    ok = lambda r: bool(r) and not r.get("error") and (r.get("dps") or 0) > 0
    both = [n for n in b if ok(a.get(n)) and ok(b[n])]
    moved = sorted(((b[n]["dps"] / a[n]["dps"] - 1, n) for n in both), key=lambda x: -abs(x[0]))
    moved = [(m, n) for m, n in moved if abs(m) >= margin]
    gone = sorted(n for n in a if ok(a[n]) and not ok(b.get(n)))
    fresh = sorted(n for n in b if ok(b[n]) and not ok(a.get(n)))
    out.append(f"{len(moved)} of {len(both)} skills moved {margin:.0%}+ (round-1 builds, no passive tree: passive changes don't show)")
    out += [f"  {m:+7.0%}  {n:<28} {a[n]['dps']:>10,} -> {b[n]['dps']:>10,}" for m, n in moved]
    if fresh:
        out.append("New (or worked only now): " + ", ".join(fresh))
    if gone:
        out.append("Gone (or broken now): " + ", ".join(gone))
    return "\n".join(out)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "run":
        arg = lambda k: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else None
        workers = int(arg("--workers") or 6)
        out = Path(arg("--out")) if arg("--out") else OUT
        run(workers, out, arg("--class"), arg("--ascendancy"))
    elif cmd == "report":
        print(report(json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))))
    elif cmd == "diff":
        print(diff(*(json.loads(Path(x).read_text(encoding="utf-8")) for x in sys.argv[2:4])))
    elif cmd == "stamp":
        print(code_stamp())
    else:
        print(__doc__)
