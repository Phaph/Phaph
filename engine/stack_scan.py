"""Stack scan: which unique, keystone or spirit buff turns a stacked stat into damage (broken-build groups B and C).

The matrix tries a piece on a plain build, where a stacking piece (Archmage, Rathpith Globe) gives almost nothing: it
only pays once its stat is piled up. Here each piece is tried with a pile of each stat (PILES), on the strongest skills
of each kind (SKILLS_PER_KIND, by round-1 damage).
  piece_gain = D(piece + pile) / D(pile) - 1      what the piece adds once the stat is piled up
  synergy    = D(piece + pile) D(base) / (D(piece) D(pile))
A row is flagged at piece_gain >= MIN_GAIN and synergy >= MIN_SYNERGY (fixed 2026-11-24 before any run).
Limits: weapon uniques are left out (as in matrix_scan); a pile is the same size on every patch; ascendancies are not
in it, so Gemling-style doublers are only seen through their items.

  python stack_scan.py run [--workers 6] [--out data/breaker/stack.json]     (resumable)
  python stack_scan.py report data/breaker/stack.json
"""
from __future__ import annotations

import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ENGINE = Path(__file__).resolve().parent
OUT = ENGINE / "data" / "breaker" / "stack.json"
PILES = {"mana": "+4000 to maximum Mana", "life": "+4000 to maximum Life",
         "energy shield": "+4000 to maximum Energy Shield", "strength": "+400 to Strength",
         "dexterity": "+400 to Dexterity", "intelligence": "+400 to Intelligence",
         "evasion": "+4000 to Evasion Rating", "armour": "+4000 to Armour", "spirit": "+300 to Spirit"}
KINDS = ("Spell", "Attack", "Minion")
SKILLS_PER_KIND = 3
MIN_GAIN, MIN_SYNERGY = 0.30, 1.20
KEEP_SYNERGY = 1.05


def pile(stat: str) -> dict:
    return {"kind": "unique", "name": f"pile:{stat}", "slot": None, "mods": PILES[stat]}


def kind_of(s: dict) -> str | None:
    t = set(s["types"])
    return "Minion" if "Minion" in t else "Spell" if "Spell" in t else "Attack" if "Attack" in t else None


def flagged(d: dict) -> list[dict]:
    """Best row of each piece, strongest first."""
    best: dict[str, dict] = {}
    for skill, rec in d["skills"].items():
        for r in rec.get("rows") or []:
            if r["gain"] >= MIN_GAIN and r["synergy"] >= MIN_SYNERGY:
                if r["piece"] not in best or r["gain"] > best[r["piece"]]["gain"]:
                    best[r["piece"]] = {**r, "skill": skill}
    return sorted(best.values(), key=lambda r: -r["gain"])


def run(workers: int, out: Path) -> None:
    import generate as g
    from breaker import Bench, pieces
    from gear import make_stage
    from pob import PoB, PoBError
    from spirit import spirit_candidates

    with PoB() as p:
        catalog = p.send("skill_catalog")["skills"]
        classes = p.list_classes()
        p.new()
        catalogue = pieces(p)
    catalogue += [{"kind": "spirit", "name": n, "mods": ""} for n in spirit_candidates(catalog, False)]
    g._ALL_ASCS[:] = [(c["name"], a) for c in classes for a in c["ascendancies"]]
    done = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {"skills": {}}
    stage, lock, quick = make_stage("end"), threading.Lock(), done.setdefault("quick", {})

    def candidate(s):
        w, sub, off = (g.weapon_options(s, {}) or [(None, None, None)])[0]
        return g.Candidate(s["name"], w, sub, off, g.DEFAULT_CLASS.get("Minion" if "Minion" in s["types"] else
                           "Spell" if "Spell" in s["types"] else "", "Mercenary"), None,
                           is_minion="Minion" in s["types"], totem=s.get("totem"))

    def save():
        done["updated"] = time.strftime("%Y-%m-%d %H:%M")
        out.write_text(json.dumps(done, indent=1, ensure_ascii=False), encoding="utf-8")

    def rank(s):
        c = g.evaluate(candidate(s), stage, {}, tree=False)
        base = 0
        if not c.error:
            try:
                base = round(Bench(g._pob()).base)
            except Exception:  # noqa: BLE001
                base = 0
        with lock:
            quick[s["name"]] = base
            save()

    def one(s):
        c = g.evaluate(candidate(s), stage, {}, tree=False)
        rec: dict = {"kind": kind_of(s), "error": c.error, "rows": []}
        if not c.error:
            try:
                p = g._pob()
                bench = Bench(p)
                d0 = bench.base
                with_pile = {k: bench._dmg([pile(k)]) for k in PILES}
                rec["dps"], rec["piles"] = round(d0), {k: round(v / d0, 3) for k, v in with_pile.items()}
                for pc in catalogue:
                    grp = None
                    try:
                        if pc["kind"] == "spirit":
                            grp = p.add_skill([pc["name"]], main=False)["group"]
                        ps = [] if grp else [pc]
                        alone = bench._dmg(ps)
                        if alone <= 0:
                            continue
                        for k, dk in with_pile.items():
                            both = bench._dmg([*ps, pile(k)])
                            gain, syn = both / dk - 1, both * d0 / (alone * dk)
                            if syn >= KEEP_SYNERGY and gain > 0:
                                rec["rows"].append({"piece": f"{pc['kind']}:{pc['name']}", "stat": k,
                                                    "alone": round(alone / d0 - 1, 3), "gain": round(gain, 3),
                                                    "synergy": round(syn, 3)})
                    except PoBError:
                        pass
                    finally:
                        if grp:
                            p.remove_skill(grp)
            except Exception as e:  # noqa: BLE001 - one skill must not stop the scan
                rec["error"] = f"{type(e).__name__}: {e}"
        with lock:
            done["skills"][s["name"]] = rec
            save()
        top = sorted(rec["rows"], key=lambda r: -r["gain"])[:3]
        print(f"  {s['name']:<26} " + ", ".join(f"{r['piece']} + {r['stat']} +{r['gain']:.0%}" for r in top)
              + (f" {rec['error']}" if rec["error"] else ""), flush=True)

    mine: list = []
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        with ThreadPoolExecutor(workers, initializer=g._bind, initargs=(mine,)) as pool:
            skills = [s for s in g.main_skills(catalog, {}) if kind_of(s)]
            list(pool.map(rank, [s for s in skills if s["name"] not in quick]))
            todo = []
            for k in KINDS:
                mine_k = sorted((s for s in skills if kind_of(s) == k), key=lambda s: -quick.get(s["name"], 0))
                todo += [s for s in mine_k[:SKILLS_PER_KIND] if quick.get(s["name"], 0) > 0 and s["name"] not in done["skills"]]
            print(f"{len(catalogue)} pieces x {len(PILES)} piles on {[s['name'] for s in todo]}", flush=True)
            list(pool.map(one, todo))
    finally:
        g._close_all(mine)
    print(report(done), flush=True)


def report(d: dict) -> str:
    rows = flagged(d)
    out = [f"{len(d['skills'])} skills scanned; {len(rows)} pieces flagged (+{MIN_GAIN:.0%} with a pile, synergy {MIN_SYNERGY})"]
    out += [f"  +{r['gain']:>6.0%} (alone {r['alone']:+.0%}, synergy {r['synergy']:.2f})  {r['piece']} with {r['stat']} on {r['skill']}"
            for r in rows]
    return "\n".join(out)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "run":
        run(int(a[a.index("--workers") + 1]) if "--workers" in a else 4,
            Path(a[a.index("--out") + 1]) if "--out" in a else OUT)
    elif a and a[0] == "report":
        print(report(json.loads(Path(a[1]).read_text(encoding="utf-8"))))
    else:
        print(__doc__)
