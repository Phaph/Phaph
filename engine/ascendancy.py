"""Ascendancy points again, once the build is settled (task 50).

The tree spends them before the final gear, supports and spirit buffs are in, and never takes them back. On finished
builds, spending them again was worth +48% (Titan Earthquake), +19% (Gemling Rapid Shot), and -65% on one: the greedy
search can also land lower. So the new points are kept only if the build as a whole scores higher.
"""
from __future__ import annotations

from optimize import score_of

MIN_GAIN = 0.005    # below this a change is noise
EHP_FLOOR = 0.9     # never trade more than a tenth of the toughness for damage


def better(before: dict, after: dict, def_weight: float) -> bool:
    """before / after: {"dps", "ehp", "short" (attribute points missing), "spirit" (left)}."""
    if after["short"] > before["short"] + 0.5 or after["spirit"] < min(before["spirit"], 0):
        return False
    if after["ehp"] < EHP_FLOOR * before["ehp"]:
        return False
    d = after["dps"] / max(before["dps"], 1) - 1
    e = after["ehp"] / max(before["ehp"], 1) - 1
    return d + def_weight * e > MIN_GAIN


def respend(pob, tree: dict, points: int, fields: list[str], metric: str, def_weight: float, goals=None, log=print) -> bool:
    """Spend the ascendancy points again for the build as it is now; put the old ones back unless it scores better.
    Updates tree["steps"] (the order to take passives). True if the points changed."""
    ids = pob.send("allocated").get("ascendancy") or []
    if not points or not ids:
        return False

    def measure() -> dict:
        short = pob.send("balance_attributes").get("short") or {}
        o = pob.calc([*fields, "TotalEHP", "SpiritUnreserved"])
        return {"dps": score_of(o, metric), "ehp": o.get("TotalEHP") or 0, "spirit": o.get("SpiritUnreserved") or 0,
                "short": sum(short.values()) if isinstance(short, dict) else 0}

    before, xml = measure(), pob.save_xml()
    pob.send("dealloc_ids", ids=ids)
    res = pob.optimise_tree(def_weight=def_weight, metric=metric, goals=goals, points=0, ascendancy_points=points, refine=False)
    after = measure()
    if not better(before, after, def_weight):
        pob.load_xml(xml)
        return False
    tree["steps"] = [s for s in res["steps"] if s.get("ascendancy")] + [s for s in tree["steps"] if not s.get("ascendancy")]
    log(f"  ascendancy respent: {after['dps'] / max(before['dps'], 1) - 1:+.1%} damage score, "
        f"{after['ehp'] / max(before['ehp'], 1) - 1:+.1%} EHP")
    return True
