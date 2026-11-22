"""Unique x skill and keystone x skill matrix: which unique or keystone is far better on one skill than on the rest.

The pair scan (breaker.py pairs) tries every unique and keystone, but only on the ~31 saved builds' skills, and only the
30 best singles go into pairs. A unique that is ordinary on most skills and broken on one particular skill (a classic
broken-build shape, research/broken_builds.md group I) is invisible there. This scan builds every main-capable skill
the quick round-1 way and measures each non-weapon unique (top rolls) and each keystone on it alone, against a
pinnacle boss, reusing breaker.Bench. A gain far above what that piece usually gives is flagged: an interaction.

Weapon uniques are not in it yet: their local mods ("Adds X to Y") would apply globally through the custom modifier box.

  python matrix_scan.py run [--workers 6] [--out data/breaker/matrix.json]   (resumable)
  python matrix_scan.py run --class Ranger --ascendancy Deadeye --out ...   (that class's weapons and ascendancy)
  python matrix_scan.py report data/breaker/matrix.json [more.json ...]   (within-family outliers)
"""
from __future__ import annotations

import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ENGINE = Path(__file__).resolve().parent
OUT = ENGINE / "data" / "breaker" / "matrix.json"
KEEP = 0.05   # store gains of at least +5%


def run(workers: int, out: Path, cls: str | None = None, asc: str | None = None) -> None:
    import generate as g
    from breaker import Bench, pieces
    from gear import make_stage
    from pob import PoB, PoBError

    with PoB() as p:
        catalog = p.send("skill_catalog")["skills"]
        classes = p.list_classes()
        p.new()
        catalogue = pieces(p)
    g._ALL_ASCS[:] = [(c["name"], a) for c in classes for a in c["ascendancies"]]
    skills = g.main_skills(catalog, {})
    done = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {"skills": {}}
    todo = [s for s in skills if s["name"] not in done["skills"]]
    print(f"{len(skills)} skills x {len(catalogue)} uniques/keystones, {len(todo)} skills to go, {workers} workers",
          flush=True)
    stage = make_stage("end")
    lock = threading.Lock()

    def one(s):
        opts = g.weapon_options(s, {})
        # Lodestone has no class-weapon rule (Kyle 2026-11-22): every skill on every class, with its ascendancy's passives.
        w, sub, off = (opts or [(None, None, None)])[0]
        c = g.Candidate(s["name"], w, sub, off, cls or g.DEFAULT_CLASS.get("Minion" if "Minion" in s["types"] else
                        "Spell" if "Spell" in s["types"] else "", "Mercenary"), asc, is_minion="Minion" in s["types"],
                        totem=s.get("totem"))
        c = g.evaluate(c, stage, {}, tree=False)
        asc_nodes = []
        if asc and not c.error:
            from breaker import ascendancy_passives
            asc_nodes = ascendancy_passives(g._pob(), stage)
        rec = {"weapon": g.weapon_key(w, sub), "types": sorted(s["types"]), "error": c.error, "gains": {}}
        if asc_nodes:
            rec["ascendancy_nodes"] = asc_nodes
        if not c.error:
            try:
                bench = Bench(g._pob())
                rec["dps"] = round(bench.base)
                if bench.base > 0:
                    for piece in catalogue:
                        try:
                            v = bench.gain([piece])
                        except PoBError:
                            continue
                        if v >= KEEP:
                            rec["gains"][f"{piece['kind']}:{piece['name']}"] = round(v, 3)
            except Exception as e:  # noqa: BLE001 - one skill must not stop the scan
                rec["error"] = f"{type(e).__name__}: {e}"
        with lock:
            done["skills"][s["name"]] = rec
            done["updated"] = time.strftime("%Y-%m-%d %H:%M")
            out.write_text(json.dumps(done, indent=1, ensure_ascii=False), encoding="utf-8")
        top = sorted(rec["gains"].items(), key=lambda kv: -kv[1])[:3]
        print(f"  {s['name']:<28} " + ", ".join(f"{k.split(':', 1)[1]} +{v:.0%}" for k, v in top), flush=True)

    mine: list = []
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        with ThreadPoolExecutor(workers, initializer=g._bind, initargs=(mine,)) as pool:
            list(pool.map(one, todo))
    finally:
        g._close_all(mine)
    print(report(done), flush=True)


def outliers(d: dict, margin: float = 0.25, floor: float = 0.30) -> list[tuple[str, str, float, float]]:
    """(skill, piece, gain, gain above that piece's usual) where a piece helps one skill far more than it usually
    helps (median over every scanned skill, skills under +5% counting as no gain)."""
    n_ok = sum(1 for r in d["skills"].values() if not r.get("error"))
    by_piece: dict[str, list[float]] = {}
    for r in d["skills"].values():
        for k, v in (r.get("gains") or {}).items():
            by_piece.setdefault(k, []).append(v)
    usual = {}
    for k, vals in by_piece.items():
        vals = sorted(vals + [0.0] * max(n_ok - len(vals), 0))
        usual[k] = vals[len(vals) // 2]
    rows = [(n, k, v, v - usual[k]) for n, r in d["skills"].items() for k, v in (r.get("gains") or {}).items()
            if v >= floor and v - usual[k] >= margin]
    return sorted(rows, key=lambda x: -x[3])


KINDS = ("Minion", "Spell", "Attack")
ELEMENTS = ("Fire", "Cold", "Lightning", "Physical", "Chaos")
MIN_PEERS = 4


def _family(types: set[str], weapon: str | None) -> tuple[str, str | None, frozenset]:
    kind = next((k for k in KINDS if k in types), "Other")
    return kind, weapon if kind == "Attack" else None, frozenset(types & set(ELEMENTS))


def peers_of(name: str, skills: dict, types: dict[str, set[str]]) -> list[str]:
    """Skills of the same family: same kind (minion / spell / attack), the same weapon for attacks, and at least one
    damage type in common. Fireflower on a fire spell is compared with other fire spells, not with every skill."""
    kind, weapon, elems = _family(types.get(name, set()), skills[name].get("weapon"))
    out = []
    for n, r in skills.items():
        if n == name or r.get("error"):
            continue
        k2, w2, e2 = _family(types.get(n, set()), r.get("weapon"))
        if k2 == kind and w2 == weapon and (elems & e2 or not elems and not e2):
            out.append(n)
    return out


def family_outliers(d: dict, types: dict[str, set[str]] | None = None, margin: float = 0.25,
                    floor: float = 0.30) -> list[tuple[str, str, float, float, int]]:
    """(skill, piece, gain, gain above its family's usual, family size): a piece far better on one skill than on that
    skill's own family. Best-in-slot for a whole family (a fire unique on fire spells, a crossbow unique on crossbow
    skills) is not flagged; a true one-skill interaction is. Families under MIN_PEERS skills use every skill instead."""
    skills = {n: r for n, r in d["skills"].items() if not r.get("error")}
    types = types or {n: set(r.get("types") or []) for n, r in skills.items()}
    rows = []
    cache: dict[tuple, list[str]] = {}
    for n, r in skills.items():
        key = _family(types.get(n, set()), r.get("weapon"))
        if key not in cache:
            cache[key] = peers_of(n, skills, types) + [n]
        fam = [x for x in cache[key] if x != n]
        pool = fam if len(fam) >= MIN_PEERS else [x for x in skills if x != n]
        for k, v in (r.get("gains") or {}).items():
            if v < floor:
                continue
            vals = sorted((skills[x].get("gains") or {}).get(k, 0.0) for x in pool)
            usual = vals[len(vals) // 2] if vals else 0.0
            if v - usual >= margin:
                rows.append((n, k, v, v - usual, len(fam)))
    return sorted(rows, key=lambda x: -x[3])


BROAD_SKILLS = 5   # strong (+30%+) on more skills than this: best-in-slot for a kind of build, not an interaction


def strong_counts(d: dict, floor: float = 0.30) -> dict[str, int]:
    counts: dict[str, int] = {}
    for r in d["skills"].values():
        for k, v in (r.get("gains") or {}).items():
            if v >= floor:
                counts[k] = counts.get(k, 0) + 1
    return counts


def report(d: dict, top: int = 40, types: dict[str, set[str]] | None = None) -> str:
    rows = family_outliers(d, types)
    counts = strong_counts(d)
    one = [r for r in rows if counts.get(r[1], 0) <= BROAD_SKILLS]
    broad = sorted({k for k, n in counts.items() if n > BROAD_SKILLS}, key=lambda k: -counts[k])
    out = [f"{len(d['skills'])} skills scanned; {len(outliers(d))} flags against all skills, {len(rows)} against "
           f"the skill's own family, {len(one)} on {BROAD_SKILLS} skills or fewer (true one-skill interactions).",
           "One-skill interactions (gain vs the family's median; family size):"]
    sys.path.insert(0, str(Path(__file__).parent / "tools"))
    from unsupported_lines import flagged
    shaky = flagged({k.split(":", 1)[1] for k in counts} | {r[1].split(":", 1)[1] for r in rows})
    tag = lambda k: "  (PoB can't read a line: check data/breaker/unsupported.txt)" if k.split(":", 1)[1] in shaky else ""
    out += [f"  +{v:>6.0%} (family usual +{v - x:.0%}, {nf} peers)  {k.split(':', 1)[1]:<28} on {n}  [{k.split(':')[0]}]"
            f"{tag(k)}" for n, k, v, x, nf in one[:top]]
    out.append(f"Broad (+30%+ on more than {BROAD_SKILLS} skills: best-in-slot for a kind of build, not an interaction):")
    out += [f"  {k.split(':', 1)[1]:<28} strong on {counts[k]} skills  [{k.split(':')[0]}]{tag(k)}" for k in broad[:15]]
    return "\n".join(out)


def load_types() -> dict[str, set[str]]:
    from pob import PoB
    with PoB() as p:
        return {s["name"]: set(s["types"]) for s in p.send("skill_catalog")["skills"]}


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "run":
        arg = lambda k: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else None
        run(int(arg("--workers") or 6), Path(arg("--out")) if arg("--out") else OUT, arg("--class"), arg("--ascendancy"))
    elif cmd == "report":
        types = load_types()
        for f in sys.argv[2:]:
            if len(sys.argv) > 3:
                print(f"== {Path(f).stem}")
            print(report(json.loads(Path(f).read_text(encoding="utf-8")), types=types))
    else:
        print(__doc__)
