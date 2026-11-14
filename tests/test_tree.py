"""Passive tree data for the website's viewer (engine/tree.py), from PoB's bundled tree."""
import math

from tree import compact, versions


def test_tree_compacts_and_positions_make_sense():
    t = compact()
    assert t["version"] == versions()[-1]
    assert len(t["nodes"]) > 3000 and len(t["edges"]) > 3000
    # Connected passives sit close together (a wrong group offset puts them thousands of units apart).
    lengths = sorted(math.dist(t["nodes"][str(e[0])][:2], t["nodes"][str(e[1])][:2]) for e in t["edges"]
                     if not t["nodes"][str(e[0])][5] and not t["nodes"][str(e[1])][5])
    assert lengths[len(lengths) // 2] < 600
    kinds = {n[2] for n in t["nodes"].values()}
    assert {"k", "n", "s"} <= kinds
    assert any(len(e) == 5 for e in t["edges"])   # arcs around group centres
