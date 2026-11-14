"""Spirit: fill the spirit pool with the persistent skills (auras, heralds, buffs, extra
minions) that add the most to the build, one at a time, scored by PoB."""
from __future__ import annotations

from optimize import CLEAR_FIELDS, DPS_FIELDS, clear_score, score_of, total_dps
from pob import PoB, PoBError

FIELDS = [*DPS_FIELDS, *CLEAR_FIELDS, "TotalEHP", "Spirit", "SpiritUnreserved"]
SKIP_TYPES = {"Meta"}   # Cast on X style skills need their own linked spells; handled elsewhere


def spirit_candidates(catalog: list[dict], minion_build: bool) -> list[str]:
    names = []
    for s in catalog:
        types = set(s["types"])
        if "Persistent" not in types or not s.get("spirit") or types & SKIP_TYPES:
            continue
        if types & {"Buff", "Aura", "Herald"} or (minion_build and "Minion" in types):
            names.append(s["name"])
    return sorted(set(names))


def optimise_spirit(pob: PoB, catalog: list[dict], mode: str = "bossing", minion_build: bool = False,
                    def_weight: float = 0.25, min_gain: float = 0.01, metric: str | None = None,
                    log=print) -> list[str]:
    """Returns the persistent skills chosen, in the order they were added. They stay in the build."""
    dps = (lambda o: score_of(o, metric)) if metric else (clear_score if mode == "mapping" else total_dps)
    cands = spirit_candidates(catalog, minion_build)
    # Heralds and extra minions add damage of their own, which only Full DPS counts.
    pob.use_full_dps()
    chosen: list[str] = []
    while True:
        out0 = pob.calc(FIELDS)
        if out0.get("SpiritUnreserved", 0) <= 0:
            break
        d0, e0 = max(dps(out0), 1), max(out0.get("TotalEHP", 0), 1)
        remaining = [c for c in cands if c not in chosen]
        if not remaining:
            break
        slot = pob.add_skill([remaining[0]], main=False, full_dps=True)["group"]
        best, best_score = None, min_gain
        for c in remaining:
            try:
                res = pob.try_skill(slot, [c], FIELDS, keep_main=True)
            except PoBError:
                continue
            o = res["output"]
            if o.get("SpiritUnreserved", -1) < 0 or res["warnings"]:
                continue
            sc = (dps(o) - d0) / d0 + def_weight * (o.get("TotalEHP", 0) - e0) / e0
            if sc > best_score:
                best, best_score = c, sc
        if not best:
            pob.remove_skill(slot)
            break
        pob.try_skill(slot, [best], FIELDS, keep_main=True)
        pob.send("sync_minion_counts")
        chosen.append(best)
        log(f"  spirit: + {best} ({best_score:+.1%})")
    return chosen
