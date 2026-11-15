"""What a PoB update (above all 1.0) added, removed or reworked, against a saved snapshot.

    python tools/catalog_diff.py snapshot      # save the installed PoB's catalog to data/catalog_snapshot.json
    python tools/catalog_diff.py diff          # compare the installed PoB with that snapshot
    python tools/catalog_diff.py diff --all    # list every name, not the first 25 per section

Covers skill gems (with their skill tags and weapons), support gems, uniques, item bases, classes and ascendancies,
and the passive tree (notables, keystones, ascendancy nodes). "Reworked" means the entry's data changed: gem stats
or levels, a unique's mods, a base's stats, a node's text.

The end of the diff lists what our own code may need: skill tags that no prompt word reaches (generate.KIND_TYPES)
and names our code uses that are gone (tools/preflight.py has the full check).
"""
import hashlib
import json
import sys
import time
from pathlib import Path

ENGINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ENGINE))

from pob import PoB  # noqa: E402

SNAPSHOT = ENGINE / "data" / "catalog_snapshot.json"


def digest(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def take() -> dict:
    with PoB() as p:
        raw = p.send("catalog_snapshot")
        skills = p.send("skill_catalog")["skills"]
        classes = {c["name"]: sorted(c["ascendancies"]) for c in p.list_classes()}
        version = p.version
    nodes: dict = {}
    for n in raw["tree"]["nodes"]:
        key = f'{n["asc"]}: {n["name"]}' if n.get("asc") else n["name"]
        nodes.setdefault(key, []).append(digest(n["text"]))
    return {
        "pob_version": version,
        "taken": time.strftime("%Y-%m-%d"),
        "gems": {g["name"]: {"support": g["support"], "tags": g["tags"], "hash": digest(g["text"])}
                 for g in raw["gems"]},
        "skills": {s["name"]: {"types": s["types"], "weapons": s["weapons"]} for s in skills},
        "uniques": {u["name"]: digest(u["text"]) for u in raw["uniques"]},
        "bases": {b["name"]: {"type": b["type"], "sub": b.get("subType"), "hash": digest(b["text"])}
                  for b in raw["bases"]},
        "classes": classes,
        "tree": {"version": raw["tree"]["version"], "counts": raw["tree"]["counts"],
                 "nodes": {k: sorted(v) for k, v in nodes.items()}},
    }


def compare(old: dict, new: dict, label: str, changed=lambda a, b: a != b) -> dict:
    return {
        "new": sorted(set(new) - set(old)),
        "removed": sorted(set(old) - set(new)),
        "reworked": sorted(k for k in set(old) & set(new) if changed(old[k], new[k])),
        "label": label,
    }


def report(old: dict, new: dict, show_all: bool = False) -> None:
    limit = None if show_all else 25
    print(f"PoB {old['pob_version']} (snapshot {old['taken']})  ->  PoB {new['pob_version']} (installed)")
    sections = [
        compare({k: v for k, v in old["gems"].items() if not v["support"]},
                {k: v for k, v in new["gems"].items() if not v["support"]}, "skill gems"),
        compare({k: v for k, v in old["gems"].items() if v["support"]},
                {k: v for k, v in new["gems"].items() if v["support"]}, "support gems"),
        compare(old["uniques"], new["uniques"], "uniques"),
        compare(old["bases"], new["bases"], "item bases"),
        compare(old["tree"]["nodes"], new["tree"]["nodes"], "tree notables, keystones, ascendancy nodes"),
    ]
    for s in sections:
        print(f"\n== {s['label']}: {len(s['new'])} new, {len(s['removed'])} removed, {len(s['reworked'])} reworked")
        for kind in ("new", "removed", "reworked"):
            names = s[kind]
            if names:
                more = f" ... (+{len(names) - limit})" if limit and len(names) > limit else ""
                print(f"  {kind}: {', '.join(names[:limit])}{more}")

    # Skill tags and weapons of skills that stayed.
    tag_changes = [f'{k}: {sorted(set(old["skills"][k]["types"]) ^ set(v["types"]))}'
                   for k, v in new["skills"].items() if k in old["skills"]
                   and set(old["skills"][k]["types"]) != set(v["types"])]
    if tag_changes:
        print(f"\n== skill tag changes ({len(tag_changes)}): " + "; ".join(tag_changes[:limit]))

    print("\n== classes and ascendancies")
    for cls in sorted(set(old["classes"]) | set(new["classes"])):
        a, b = set(old["classes"].get(cls, [])), set(new["classes"].get(cls, []))
        if cls not in old["classes"]:
            print(f"  new class {cls}: {sorted(b)}")
        elif cls not in new["classes"]:
            print(f"  removed class {cls}")
        elif a != b:
            print(f"  {cls}: new {sorted(b - a)}, removed {sorted(a - b)}")
    t0, t1 = old["tree"], new["tree"]
    print(f"\n== tree {t0['version']} -> {t1['version']}: node counts {t0['counts']} -> {t1['counts']}")

    # What our own code may need.
    from generate import HELPER_TYPES, KIND_TYPES, NOT_MAIN
    known = set(KIND_TYPES.values()) | set(HELPER_TYPES.values()) | NOT_MAIN
    old_types = {t for s in old["skills"].values() for t in s["types"]}
    new_types = {t for s in new["skills"].values() for t in s["types"]}
    print("\n== for our code")
    print(f"  new skill tags no prompt word reaches (generate.KIND_TYPES / prompt.KINDS): "
          f"{sorted(new_types - old_types - known) or 'none'}")
    print(f"  skill tags gone: {sorted(old_types - new_types) or 'none'}")
    print("  run tools/preflight.py for every name the engine uses")


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in {"snapshot", "diff"}:
        print(__doc__)
        return 2
    new = take()
    if sys.argv[1] == "snapshot":
        SNAPSHOT.write_text(json.dumps(new, indent=0, sort_keys=True, ensure_ascii=False), encoding="utf-8")
        print(f"saved {SNAPSHOT.name}: PoB {new['pob_version']}, {len(new['gems'])} gems, {len(new['uniques'])} "
              f"uniques, {len(new['bases'])} bases, {len(new['tree']['nodes'])} tree nodes")
        return 0
    if not SNAPSHOT.exists():
        print("no snapshot yet: run `catalog_diff.py snapshot` on the old PoB first")
        return 2
    report(json.loads(SNAPSHOT.read_text(encoding="utf-8")), new, "--all" in sys.argv)
    return 0


if __name__ == "__main__":
    sys.exit(main())
