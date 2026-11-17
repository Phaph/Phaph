"""Weapon set passives: a build that uses two weapon sets can give each set passives of its own.

PoE 2 gives every character weapon set passive points (quest rewards, plus Weapon Master's "N passive skill points
become weapon set skill points" on Witchhunter). With one weapon set they act like normal points, which is how the
tree optimiser spends them. A build that swaps to weapon set 2 (a boss skill on another weapon) can do better: the
points' worth of shared passives that set 2's skill needs least become set 1 only (they keep working on set 1), and
the freed points are spent again, on set 2 only, for set 2's skill. Kept only if set 2's damage rises; otherwise the
tree is put back exactly as it was.
"""
from __future__ import annotations

from optimize import score_of
from pob import PoB, PoBError

FIELDS = ["TotalDPS", "TotalDotDPS", "FullDPS", "FullDotDPS", "CombinedDPS", "MinionDPS", "BleedDPS", "PoisonDPS",
          "IgniteDPS", "TotalEHP"]
MIN_GAIN = 0.02


def specialise_set2(pob: PoB, set2_group: int, set1_group: int, metric: str, def_weight: float = 0.25,
                    log=lambda *a: None) -> dict | None:
    """Split the weapon set passive points between the two sets. `set2_group` is the skill used on weapon set 2
    (it becomes the main skill while its passives are chosen). Returns what changed, or None (nothing kept)."""
    info = pob.send("weapon_set_points")
    points = int(info.get("points") or 0)
    if points <= 0:
        return None
    xml = pob.save_xml()
    try:
        pob.send("set_main", group=set2_group)
        before = score_of(pob.calc(FIELDS), metric)
        moved = pob.send("split_weapon_set", keep_set=1, points=points).get("moved") or []
        if not moved:
            raise LookupError
        used = pob.points().get("used", 0)
        pob.send("set_alloc_mode", mode=2)
        try:
            tree = pob.optimise_tree(points=used + len(moved), def_weight=def_weight, metric=metric, refine=False)
        finally:
            pob.send("set_alloc_mode", mode=0)
        after = score_of(pob.calc(FIELDS), metric)
        warn = [w for w in pob.warnings() if "weapon set" in w.lower()]
        if warn or after < before * (1 + MIN_GAIN):
            log(f"weapon sets: no gain ({after / max(before, 1) - 1:+.1%}){' ' + warn[0] if warn else ''}")
            raise LookupError
        added = [s["node"] for s in tree.get("steps") or []]
        pob.send("set_main", group=set1_group)
        log(f"weapon sets: {points} points; set 2 +{after / max(before, 1) - 1:.1%}")
        return {"points": points, "set1_only": moved, "set2_only": added, "gain": after / max(before, 1) - 1}
    except (LookupError, PoBError):
        pob.load_xml(xml)
        pob.send("set_main", group=set1_group)
        return None
