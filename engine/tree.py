"""The passive tree for the website's viewer, from Path of Building's own tree data (MIT licensed code; the tree
data itself is Grinding Gear Games' game data, which PoB ships).

compact(version) turns PoB's TreeData/<version>/tree.json (about 2 MB) into what a browser needs to draw it:
node positions, kinds, names and stats, and the connections between nodes (as arcs where the game draws arcs).
No game art is used: the website draws its own shapes.
"""
from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

from pob import VENDOR

TREE_DIR = VENDOR / "PathOfBuilding-PoE2" / "src" / "TreeData"


def versions() -> list[str]:
    return sorted((p.name for p in TREE_DIR.iterdir() if (p / "tree.json").exists()),
                  key=lambda v: [int(x) if x.isdigit() else x for x in v.split("_")])


def _kind(n: dict) -> str:
    if n.get("classesStart"):
        return "c"
    if n.get("isAscendancyStart"):
        return "A"
    if n.get("isKeystone"):
        return "k"
    if n.get("isJewelSocket"):
        return "j"
    if n.get("isNotable"):
        return "n"
    if n.get("isAttribute"):
        return "a"
    return "s"


@lru_cache(maxsize=4)
def compact(version: str | None = None) -> dict:
    version = version if version in versions() else versions()[-1]
    t = json.loads((TREE_DIR / version / "tree.json").read_text(encoding="utf-8"))
    consts, groups, raw = t["constants"], t["groups"], t["nodes"]
    radii, angles = consts["orbitRadii"], consts["orbitAnglesByOrbit"]

    def group_of(n):
        g = n.get("group")
        return groups[g - 1] if isinstance(g, int) and 0 < g <= len(groups) else None   # groups are numbered from 1

    nodes, pos = {}, {}
    for key, n in raw.items():
        if not key.isdigit() or n.get("isOnlyImage"):
            continue
        g = group_of(n)
        if not g:
            continue
        o, oi = n.get("orbit", 0), n.get("orbitIndex", 0)
        a = angles[o][oi] if o < len(angles) and oi < len(angles[o]) else 0
        x, y = g["x"] + math.sin(a) * radii[o], g["y"] - math.cos(a) * radii[o]
        pos[int(key)] = (x, y, n.get("group"), o)
        nodes[key] = [round(x), round(y), _kind(n), n.get("name", ""), n.get("stats", []), n.get("ascendancyName")]

    edges, seen = [], set()
    for key, n in raw.items():
        a = int(key) if key.isdigit() else None
        if a not in pos:
            continue
        for c in n.get("connections", []):
            b = c.get("id")
            if b not in pos or (min(a, b), max(a, b)) in seen:
                continue
            seen.add((min(a, b), max(a, b)))
            (ax, ay, ag, ao), (bx, by, bg, bo) = pos[a], pos[b]
            if ag == bg and ao == bo and ao > 0:
                g = group_of(n)   # same orbit of the same group: the game draws an arc around the group centre
                edges.append([a, b, round(g["x"]), round(g["y"]), radii[ao]])
            else:
                edges.append([a, b])

    main = [v for v in nodes.values() if not v[5]]
    bounds = [min(v[0] for v in main), min(v[1] for v in main), max(v[0] for v in main), max(v[1] for v in main)]
    return {"version": version, "nodes": nodes, "edges": edges, "bounds": bounds}
