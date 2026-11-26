"""ascendancy.py: points spent again only when the whole build is better."""
from ascendancy import better, respend

B = {"dps": 100.0, "ehp": 100.0, "short": 0, "spirit": 5}


def test_better():
    assert better(B, {**B, "dps": 110}, 0.25)
    assert not better(B, {**B, "dps": 100.1}, 0.25)                     # noise
    assert not better(B, {**B, "dps": 35}, 0.25)                        # greedy landed lower
    assert not better(B, {**B, "dps": 200, "ehp": 85}, 0.25)            # too fragile
    assert not better(B, {**B, "dps": 150, "short": 20}, 0.25)          # gear can't be worn
    assert not better(B, {**B, "dps": 150, "spirit": -10}, 0.25)        # overdrawn
    assert better({**B, "spirit": -10}, {**B, "dps": 150, "spirit": -10}, 0.25)   # was overdrawn before: not its doing


def test_respend_puts_the_old_points_back_or_keeps_the_better(pob):
    pob.new()
    pob.set_class("Sorceress", "Stormweaver")
    pob.set_level(90)
    pob.add_skill(["Spark"])
    fields = ["TotalDPS", "TotalDotDPS", "TotalEHP"]
    tree = pob.optimise_tree(points=10, ascendancy_points=8, refine=False)
    start = pob.send("allocated")
    assert len(start["ascendancy"]) == 8
    n_main = len([s for s in tree["steps"] if not s.get("ascendancy")])
    if not respend(pob, tree, 8, fields, "total", 0.25, log=lambda *a: None):
        assert pob.send("allocated")["nodes"] == start["nodes"]         # the old points are back, all of them
    alloc = set(pob.send("allocated")["nodes"])
    assert len([s for s in tree["steps"] if not s.get("ascendancy")]) == n_main
    assert all(set(s["path"]) <= alloc for s in tree["steps"])
    # the worst case: the new points are worse, so nothing may change
    import ascendancy
    keep, ascendancy.better = ascendancy.better, lambda *a: False
    try:
        now = pob.send("allocated")["nodes"]
        assert not respend(pob, tree, 8, fields, "total", 0.25, log=lambda *a: None)
        assert pob.send("allocated")["nodes"] == now
    finally:
        ascendancy.better = keep
