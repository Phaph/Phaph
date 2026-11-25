"""Breaker text scanner: read every gem, unique and passive for wording that has broken the game before.

research/broken_builds.md sorted every broken build of PoE 2 patches 0.1-0.5.5 into ten groups by WHY it broke. Most of
them can be spotted from the item or gem text alone, before any calculation: a "more" multiplier per unit of something,
a count with no maximum, a cost that can reach zero, a trigger, a defence that can reach 100%, wording that replaces
a rule ("instead of"). This scanner flags every line like that, so the scaler scan, the trigger estimator and Kyle's
in-game tests start from a short list instead of the whole game.

It runs from PoB's data only, so it works on patch day as soon as PoB (or our own export) has the new text, and
`diff` lists only what is new or changed since the last scan (new content breaks first, research pattern 3).

  python text_scan.py scan [--out data/breaker/text_scan.json]
  python text_scan.py diff OLD.json NEW.json
  python text_scan.py report data/breaker/text_scan.json
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ENGINE = Path(__file__).resolve().parent
OUT = ENGINE / "data" / "breaker" / "text_scan.json"

# Group letters follow research/broken_builds.md Part 2. Each rule: (group, name, pattern, why).
RULES = [
    ("A", "more per unit", r"\bmore\b[^.]*\bper\b|\bper\b[^.]*\bmore\b",
     "A 'more' multiplier that grows per unit of something: uncapped units make it multiply without limit"),
    ("A", "more after time", r"\bmore\b[^.]*\bafter\b[^.]*\bseconds?\b|\bafter\b[^.]*\bseconds?\b[^.]*\bmore\b",
     "A 'more' bonus after a delay: always on against a boss that stands still"),
    ("B", "stat as extra damage", r"\bgains?\b[^.]*\bas extra\b|\bas extra\b[^.]*\bdamage\b",
     "Damage gained as extra from something: stacks with everything else"),
    ("B", "damage per stat", r"\bdamage\b[^.]*\bper\b[^.]*\b(strength|dexterity|intelligence|mana|life|energy shield|evasion|armour|spirit|rage|charge|attribute)",
     "Damage scaling from a stat the build can stack"),
    ("B", "uses another stat", r"\b(instead of|in place of)\b[^.]*\b(mana|life|energy shield|spirit)\b|\bcost[s]?\b[^.]*\b(life|energy shield)\b",
     "A resource swap: one stat starts doing another stat's job (the most-nerfed shape when it also gives defence)"),
    ("D", "trigger", r"\btrigger(s|ed)?\b|\bon (kill|hit|crit|critical|freeze|shock|ignite|block|evade|death)\b|\bwhen you\b[^.]*\b(kill|hit|block|evade|are hit)\b",
     "A trigger: free casts if the condition can be met fast enough (needs the trigger estimator)"),
    ("D", "no cost / no cooldown", r"\bno (mana |life )?cost\b|\bcost[s]? nothing\b|\bdoes not (have|use) (a )?cooldown\b|\bignores? cooldown\b|\bcooldown recovery\b",
     "Cost or cooldown removal: the classic free-cast loop"),
    ("D", "not consumed", r"\bnot (be )?consumed?\b|\bnot consume\b|\bchance to not\b|\bwithout consuming\b",
     "A chance not to consume something: at 100% it becomes infinite"),
    ("E", "adds a count", r"\b(additional|extra|\+\d+)\b[^.]*\b(projectiles?|spirits?|clouds?|rods?|clones?|explosions?|chains?|totems?|minions?|copies|beams?|meteors?|orbs?|bolts?|pulses?)\b",
     "Adds to a count: check whether anything caps it, and how many hit one boss"),
    ("E", "repeats", r"\b(repeats?|echoe?s?|overlap|again)\b",
     "Repeats or overlaps: hits that land again on the same target"),
    ("F", "chain reaction", r"\b(explode|explodes|explosion)\b|\bwhen (an )?enem(y|ies) (dies|die|is killed)\b|\bon kill\b",
     "On-kill or explosion effects: can set off more of themselves in a pack"),
    ("G", "reaches a cap", r"\bmaximum\b[^.]*\b(block|resistance|evasion|chance)\b|\b(cannot|can't) (be|die|take)\b|\bimmune\b|\bimmunity\b|\b100%\b",
     "A defence that can reach its cap or 100%: immortality is hotfixed fast but wins launch week"),
    ("H", "condition", r"\bif you('ve| have)? (not )?(been )?hit recently\b|\bagainst (immobilised|frozen|shocked|stunned|pinned|cursed)\b|\bwhile (stationary|channelling|on full)\b",
     "A conditional bonus: is it really always on against a boss?"),
    ("J", "replaces a rule", r"\binstead\b|\breplaces?\b|\bconverted? to\b|\bcount(s)? as\b|\bbecomes?\b",
     "Wording that replaces a rule: the add-vs-replace bugs of past patches came from lines like this (test in game)"),
    ("J", "inactive weapon set", r"\bweapon set\b|\bwhile (wielding|using)\b[^.]*\bswap",
     "Effects tied to a weapon set: past bugs applied the inactive set's effects"),
]
NO_CAP = re.compile(r"\b(maximum|max|up to|limit|cannot exceed|capped)\b", re.I)
COMPILED = [(g, n, re.compile(p, re.I), w) for g, n, p, w in RULES]


def flags(line: str) -> list[dict]:
    out = []
    line = re.sub(r"no more than", "at most", line, flags=re.I)   # a limit, not a "more" multiplier
    for group, name, rx, why in COMPILED:
        if rx.search(line):
            f = {"group": group, "rule": name}
            if group in ("A", "E") and not NO_CAP.search(line):
                f["no_cap"] = True   # nothing in the line caps it
            out.append(f)
    return out


def _clean(s: str) -> str:
    return re.sub(r"\{[^}]*\}", "", s).strip()


def patched_nodes(pob) -> dict[str, list[str]]:
    """Patch-notes mode: the lines of every passive the changes file rewrote, by node id. The tree file on disk is the
    unpatched game, so without this a patched passive never shows up in the diff."""
    path = os.environ.get("PATCH_FILE")
    if not path:
        return {}
    out = {}
    for c in json.loads(Path(path).read_text(encoding="utf-8")).get("changes") or []:
        if c.get("passive"):
            for d in pob.send("node_debug", name=c["passive"])["nodes"]:
                if d["where"].startswith("tree "):
                    out[d["where"][5:]] = list(d.get("sd") or [])
    return out


def collect(pob) -> list[dict]:
    """Every text line worth reading: gem stat lines (with PoB's 'not supported' flag), unique mods, passive stats."""
    lines: list[dict] = []
    tips = pob.send("gem_tooltips")["gems"]
    for name, tl in tips.items():
        kind = "support" if len(tl) > 1 and tl[1].get("t") == "Support" else "gem"
        for ln in tl:
            if ln.get("k") in ("stat", "unsupported", "desc"):
                t = ln.get("t", "").replace("(Not supported in PoB yet)", "").strip()
                if t:
                    lines.append({"source": kind, "name": name, "line": t, "pob_blind": ln.get("k") == "unsupported"})
    seen = set()
    for u in pob.list_uniques():
        name = u["name"].split(",")[0]
        for ln in (u.get("raw") or "").split("\n")[2:]:
            if re.match(r"^[A-Za-z ]+:\s", ln) or not ln.strip():
                continue
            if (name, _clean(ln)) in seen:   # several uniques can share a name (Grand Spectrum): keep every line once
                continue
            seen.add((name, _clean(ln)))
            lines.append({"source": "unique", "name": name, "line": _clean(ln), "pob_blind": False})
    from tree import compact
    tree = compact(None)
    patched = patched_nodes(pob)
    for key, n in (tree.get("nodes") or {}).items():
        kind, name, stats, asc = n[2], n[3], patched.get(str(key), n[4] or []), n[5]
        if kind not in ("n", "k") and not asc:   # notables, keystones and every ascendancy node
            continue
        for s in stats:
            src = "ascendancy" if asc else {"n": "notable", "k": "keystone"}[kind]
            lines.append({"source": src, "name": f"{name} ({asc})" if asc else name,
                          "line": s, "pob_blind": False})
    return lines


def scan(pob) -> dict:
    hits = []
    for ln in collect(pob):
        f = flags(ln["line"])
        if f:
            hits.append({**ln, "flags": f})
    for h in hits:
        groups = {f["group"] for f in h["flags"]}
        # A rough priority: lines that combine several risky shapes, have no cap, or that PoB can't calculate come first.
        h["priority"] = (len(groups) + 2 * any(f.get("no_cap") for f in h["flags"]) + 2 * h["pob_blind"]
                         + (1 if h["source"] in ("keystone", "ascendancy", "unique") else 0))
    hits.sort(key=lambda h: (-h["priority"], h["source"], h["name"]))
    return {"pob_version": getattr(pob, "version", None), "game_patch": getattr(pob, "patch", None),
            "lines": len(hits), "hits": hits}


def diff(old: dict, new: dict) -> list[dict]:
    """Flagged lines that are new or changed since the old scan (patch day: read these first)."""
    before = {(h["source"], h["name"], h["line"]) for h in old.get("hits", [])}
    return [h for h in new.get("hits", []) if (h["source"], h["name"], h["line"]) not in before]


def report(data: dict, top: int = 40) -> str:
    from collections import Counter
    by_group = Counter(f["group"] for h in data["hits"] for f in h["flags"])
    out = [f"{data['lines']} flagged lines (PoB {data.get('pob_version')}, patch {data.get('game_patch')})",
           "by group: " + ", ".join(f"{g} {n}" for g, n in sorted(by_group.items()))]
    for h in data["hits"][:top]:
        g = "".join(sorted({f["group"] for f in h["flags"]}))
        out.append(f"  [{h['priority']}] {g:<5} {h['source']:<10} {h['name'][:32]:<32} {h['line'][:110]}"
                   + ("  (PoB can't calculate)" if h["pob_blind"] else ""))
    return "\n".join(out)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "scan":
        from pob import PoB
        out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else OUT
        with PoB() as p:
            p.new()
            data = scan(p)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
        print(report(data))
    elif cmd == "diff":
        old, new = (json.loads(Path(p).read_text(encoding="utf-8")) for p in sys.argv[2:4])
        d = diff(old, new)
        print(report({**new, "lines": len(d), "hits": d}))
    elif cmd == "report":
        print(report(json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))))
    else:
        print(__doc__)
