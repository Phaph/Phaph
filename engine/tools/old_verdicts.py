"""Task 40: did the next patch change a flagged unique, keystone or spirit buff? (PoB data of tag vs next tag.)

Rule, fixed 2026-11-24 before any valid matrix scan. The 0.1 stack scan's rows for 8 of 9 skills had been seen by then
(Irongrasp and Archmage flagged), so its verdict on Irongrasp is not blind:
  unchanged text (current variant)  -> not cut: a false alarm, unless the piece is an answer-key hit
  changed or gone                   -> listed with its changed lines; a person reads which way it went
  spirit buffs                      -> always listed (their numbers sit in skill data; read it there)
PoB's item data is kept by hand and can lag, so "unchanged" is PoB's word, not the patch notes'.

  python tools/old_verdicts.py [piece kind:name ...]     default: every piece flagged by the matrix and stack scans on disk
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE))
OLD = ENGINE / "data" / "breaker" / "old"
POB = Path.home() / "oldpob"
NEXT = {"v0.5.0": "v0.8.0", "v0.8.0": "v0.12.2", "v0.12.2": "v0.15.0", "v0.15.0": "current"}
META = re.compile(r"^(Variant|League|Source|Implicits|Requires|LevelReq|Has Alt Variant|Selected Variant|Limited to|Radius):?")


def current_lines(raw: str) -> list[str]:
    """An item's mod lines in its last variant (a line without {variant:} is in all of them)."""
    lines = [l.strip() for l in raw.strip().splitlines()][2:]          # name, base
    n = sum(l.startswith("Variant:") for l in lines)
    out = []
    for l in lines:
        if not l or META.match(l):
            continue
        m = re.match(r"\{variant:([\d,]+)\}", l)
        if m and str(n) not in m.group(1).split(","):
            continue
        out.append(re.sub(r"\{[^}]*\}", "", l))
    return out


def uniques(tag: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for f in sorted((POB / tag / "src" / "Data" / "Uniques").glob("*.lua")):
        for raw in re.findall(r"\[\[(.*?)\]\]", f.read_text(encoding="utf-8"), re.S):
            name = raw.strip().splitlines()[0].strip() if raw.strip() else ""
            if name:
                out.setdefault(name.split(",")[0], current_lines(raw))
    return out


def keystones(tag: str) -> dict[str, list[str]]:
    dirs = sorted(d for d in (POB / tag / "src" / "TreeData").iterdir() if re.fullmatch(r"\d_\d+", d.name))
    tree = json.loads((dirs[-1] / "tree.json").read_text(encoding="utf-8"))
    nodes = tree["nodes"].values() if isinstance(tree["nodes"], dict) else tree["nodes"]
    return {n["name"]: n.get("stats") or [] for n in nodes if n.get("isKeystone")}


def verdict(piece: str, tag: str, cache: dict) -> tuple[str, list[str]]:
    kind, name = piece.split(":", 1)
    if kind not in ("unique", "keystone"):
        return "read it", ["not an item or keystone"]
    load = uniques if kind == "unique" else keystones
    a, b = (cache.setdefault((kind, t), load(t)) for t in (tag, NEXT[tag]))
    if name not in a:
        return "read it", ["not found in this patch's data"]
    if name not in b:
        return "gone", a[name]
    if a[name] == b[name]:
        return "unchanged", []
    return "changed", [f"- {l}" for l in a[name] if l not in b[name]] + [f"+ {l}" for l in b[name] if l not in a[name]]


def flagged_pieces(tag: str) -> set[str]:
    from grade_old import flagged
    pieces = {r[1] for r in flagged(tag, "matrix") or []}
    f = OLD / f"{tag}_stack.json"
    log = Path.home() / "old_patch.log"
    if f.exists() and log.exists() and f"{tag} stack done" in log.read_text():   # finished scans only
        from stack_scan import flagged as stack_flagged
        pieces |= {r["piece"] for r in stack_flagged(json.loads(f.read_text(encoding="utf-8")))}
    return pieces


def main() -> None:
    cache: dict = {}
    for tag in NEXT:
        for p in sorted(sys.argv[1:] or flagged_pieces(tag)):
            v, lines = verdict(p, tag, cache)
            print(f"{tag} {p}: {v}" + "".join(f"\n      {l}" for l in lines))


if __name__ == "__main__":
    main()
