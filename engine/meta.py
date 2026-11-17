"""Off-meta toggle: builds made of what the ladder plays score lower.

data/meta_usage.json (tools/fetch_meta.py, from poe.ninja) holds the share of ladder characters using each
ascendancy, skill, unique and keystone. With the toggle on, a build's score is divided by how popular its parts
are, so the search lands on the strongest build that few people play rather than the meta one:

    factor = 1 / ((1 + SKILL_W * skill share) * (1 + ASC_W * ascendancy share))

Herald of Ice (18% of the ladder) on Gemling (32%) keeps about 1/(2.8 * 2.3) = 16% of its score; a skill used by
1% on an ascendancy used by 3% keeps about 82%. So an off-meta build wins when it is within about 5x of the meta
one, and still has to be strong to win at all.
"""
from __future__ import annotations

import json
from pathlib import Path

SKILL_W = 10.0
ASC_W = 4.0
UNIQUE_W = 6.0
META_SHARE = 0.05   # used by 5%+ of the ladder: called "meta" on the page
_USAGE: dict | None = None


def usage() -> dict:
    global _USAGE
    if _USAGE is None:
        try:
            _USAGE = json.loads((Path(__file__).parent / "data" / "meta_usage.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _USAGE = {}
    return _USAGE


def share(kind: str, name: str | None) -> float:
    """Share of ladder characters using it (0 when unknown). Unique names may be PoB's "Name, Base"."""
    if not name:
        return 0.0
    return float((usage().get(kind) or {}).get(name.split(",")[0], 0.0))


def meta_factor(skill: str | None = None, ascendancy: str | None = None, unique: str | None = None) -> float:
    f = (1 + SKILL_W * share("skill", skill)) * (1 + ASC_W * share("ascendancy", ascendancy))
    f *= 1 + UNIQUE_W * share("unique", unique)
    return 1 / f


def popularity(skill: str | None, ascendancy: str | None) -> dict:
    """What the page shows: {"skill": 0.18, "ascendancy": 0.32, "league": ..., "characters": ...}."""
    u = usage()
    return {"skill": share("skill", skill), "ascendancy": share("ascendancy", ascendancy),
            "league": u.get("league"), "characters": u.get("characters")}
