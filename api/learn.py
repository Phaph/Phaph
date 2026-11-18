"""Learning from saved builds. Nothing is trained: the builds people have made (the jobs database) and the prompt log
feed the search and Claude directly.

  winners()        bug spotting: how often each skill, ascendancy and unique wins a search it was free to win, with
                   flags for anything that wins far too often (a modelling bug, or a real over-powered build for the
                   Breaker). GET /learn/winners.
  head_starts()    strong builds from earlier searches like this one; the search re-tests them alongside its own picks
                   (generate.py "head starts"), so it is faster to find them and less likely to miss them.
  similar_builds() other finished builds with the same skill or ascendancy, given to Claude for the write-up.
  misreads()       prompts the Claude reader may have got wrong, for review; fixes go in prompt_examples.json.

Patches: every job is labelled with its game patch (api/jobs.py). Everything here reads only the current patch's
builds plus `seeds`, the old patch's winners re-tested on the new one (api/retest.py). Old builds are never deleted.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from collections import Counter
from pathlib import Path

_db: sqlite3.Connection | None = None
_patch: str | None = None
_lock = threading.Lock()

SEEDS = """
CREATE TABLE IF NOT EXISTS seeds (
    game_patch TEXT NOT NULL,
    theme TEXT NOT NULL,        -- JSON: the request fields that say what kind of build it is
    build TEXT NOT NULL,        -- JSON: skill, cls, ascendancy, weapon_type, weapon_subtype, offhand_type
    score REAL,
    old_patch TEXT,
    old_score REAL,
    created REAL
);
CREATE INDEX IF NOT EXISTS seeds_patch ON seeds (game_patch);
"""

# Request fields that describe what kind of build was asked for (for "searches like this one").
THEME_LISTS = ("damage", "kinds", "weapons", "goals", "with_types")
THEME_ONE = ("ailment", "class", "cls", "ascendancy", "skill", "mode", "anchor_unique", "anchor_keystone", "anchor_support")
BUILD_KEYS = ("skill", "cls", "ascendancy", "weapon_type", "weapon_subtype", "offhand_type", "totem")
HEAD_STARTS = 4        # past winners re-tested in a new search
MIN_SIMILAR = 0.6      # how alike two requests must be (0..1) to share head starts

# Bug spotting: something is flagged when it wins this share of the searches it was free to win (enough of them).
FLAG_SHARE = {"skill": 0.2, "ascendancy": 0.2, "unique": 0.25}
FLAG_MIN_SEARCHES = 10


def bind(db_path: str, patch: str) -> None:
    global _db, _patch
    with _lock:
        _db = sqlite3.connect(db_path, check_same_thread=False)
        _db.row_factory = sqlite3.Row
        _db.executescript(SEEDS)
        _patch = patch


def patch() -> str | None:
    return _patch


def _rows(kind: str, game_patch: str | None = None):
    if _db is None:
        return []
    with _lock:
        return _db.execute("SELECT id, request, result FROM jobs WHERE kind=? AND status='done' AND game_patch=? "
                           "ORDER BY created DESC", (kind, game_patch or _patch)).fetchall()


def _theme(req: dict) -> set[str]:
    out = set()
    for k in THEME_LISTS:
        out |= {f"{k}:{str(v).lower()}" for v in req.get(k) or []}
    for k in THEME_ONE:
        if req.get(k):
            out.add(f"{'class' if k == 'cls' else k}:{str(req[k]).lower()}")
    return out


def similarity(a: dict, b: dict) -> float:
    """How alike two build requests are, 0..1. Two empty requests ("best build") count as alike."""
    ta, tb = _theme(a), _theme(b)
    if not ta and not tb:
        return 1.0
    return len(ta & tb) / len(ta | tb)


def _fits(build: dict, req: dict) -> bool:
    """A past build can be a head start only if it obeys this request's hard choices."""
    if req.get("skill") and build.get("skill") != req["skill"]:
        return False
    if req.get("ascendancy") and build.get("ascendancy") != req["ascendancy"]:
        return False
    cls = req.get("class") or req.get("cls")
    if cls and (build.get("cls") or "").lower() != cls.lower():
        return False
    if req.get("weapons") and (build.get("weapon_type") or "").lower() not in {w.lower() for w in req["weapons"]}:
        return False
    return True


def head_starts(req: dict, n: int = HEAD_STARTS) -> list[dict]:
    """The strongest builds from earlier searches like this one (this patch only, plus re-tested seeds)."""
    if _db is None or req.get("random"):
        return []
    found: list[tuple[float, float, dict]] = []   # (similarity, relative strength, build)
    for row in _rows("generate"):
        try:
            res = json.loads(row["result"])["result"]
        except (ValueError, KeyError, TypeError):
            continue
        past = res.get("request") or {}
        if past.get("random"):
            continue
        sim = similarity(req, past)
        if sim < MIN_SIMILAR:
            continue
        for r in (res.get("ranked") or [])[:3]:
            found.append((sim, r.get("relative") or 0, {k: r.get(k) for k in BUILD_KEYS}))
    with _lock:
        seeds = _db.execute("SELECT theme, build, score FROM seeds WHERE game_patch=?", (_patch,)).fetchall()
    for s in seeds:
        sim = similarity(req, json.loads(s["theme"]))
        if sim >= MIN_SIMILAR:
            found.append((sim, 1.0, json.loads(s["build"])))
    out, seen = [], set()
    for sim, rel, b in sorted(found, key=lambda x: (-x[0], -x[1])):
        key = (b.get("skill"), b.get("ascendancy"), b.get("weapon_type"))
        if key in seen or not b.get("skill") or not _fits(b, req):
            continue
        seen.add(key)
        out.append(b)
        if len(out) >= n:
            break
    return out


def winners(game_patch: str | None = None) -> dict:
    """Bug spotting. A skill only counts in searches that didn't name a skill (same for ascendancy, unique), so
    "a Hexblast build" doesn't make Hexblast look dominant."""
    free = Counter()
    wins = {"skill": Counter(), "ascendancy": Counter(), "unique": Counter()}
    searches = 0
    for row in _rows("generate", game_patch):
        try:
            res = json.loads(row["result"])["result"]
        except (ValueError, KeyError, TypeError):
            continue
        req, best = res.get("request") or {}, res.get("best") or {}
        if req.get("random") or not best.get("skill"):
            continue
        searches += 1
        if not req.get("skill"):
            free["skill"] += 1
            wins["skill"][best["skill"]] += 1
        if not req.get("ascendancy"):
            free["ascendancy"] += 1
            wins["ascendancy"][best.get("ascendancy")] += 1
        if not req.get("anchor_unique"):
            free["unique"] += 1
    # Uniques come from the finished guides (generate results carry no gear).
    for row in _rows("guide", game_patch):
        try:
            g = json.loads(row["result"])
        except ValueError:
            continue
        if (g.get("spec") or {}).get("anchor_unique"):
            continue
        end = next((s for s in g.get("stages") or [] if s.get("stage") == "end"), None)
        if not end:
            continue
        free["unique_guides"] += 1
        for u in {(x.get("unique") or "").split(",")[0] for x in end.get("gear") or [] if x.get("unique")}:
            wins["unique"][u] += 1
    out = {"game_patch": game_patch or _patch, "searches": searches, "flags": []}
    for kind, counter in wins.items():
        total = free["unique_guides"] if kind == "unique" else free[kind]
        out[kind] = [{"name": k, "wins": v, "share": round(v / total, 3) if total else 0}
                     for k, v in counter.most_common(15)]
        for e in out[kind]:
            if total >= FLAG_MIN_SEARCHES and e["share"] >= FLAG_SHARE[kind] and e["wins"] >= 3:
                what = "guides" if kind == "unique" else "searches"
                out["flags"].append({"kind": kind, "name": e["name"], "share": e["share"],
                                     "why": f"{e['name']} {'is worn in' if kind == 'unique' else 'wins'} "
                                            f"{e['share']:.0%} of {total} {what} that left the {kind} open. "
                                            f"Check it: a modelling bug, or a real over-powered pick for the Breaker."})
    return out


def similar_builds(spec: dict, n: int = 4) -> list[dict]:
    """Other finished builds this patch with the same skill or ascendancy, for the write-up's context."""
    out = []
    for row in _rows("guide"):
        try:
            g = json.loads(row["result"])
        except ValueError:
            continue
        s = g.get("spec") or {}
        same_skill, same_asc = s.get("skill") == spec.get("skill"), s.get("ascendancy") == spec.get("ascendancy")
        if not (same_skill or same_asc) or (same_skill and same_asc and s.get("weapon_type") == spec.get("weapon_type")):
            continue
        end = next((x for x in g.get("stages") or [] if x.get("stage") == "end"), None)
        if not end or not end.get("dps"):
            continue
        out.append({"skill": s.get("skill"), "ascendancy": s.get("ascendancy"), "weapon": s.get("weapon_type"),
                    "mapping_dps": round(end.get("dps") or 0), "boss_dps": round(end.get("boss_dps") or 0),
                    "life": round((end.get("stats") or {}).get("Life") or 0),
                    "same": "skill and ascendancy" if same_skill and same_asc else "skill" if same_skill else "ascendancy"})
        if len(out) >= n:
            break
    return out


def misreads(log_path: str | Path, catalog: dict, last: int = 300) -> list[dict]:
    """Prompts the Claude reader may have misread: words it couldn't use, or a different skill / class /
    ascendancy / anchor than the word-list reader found. For a person to review; confirmed fixes go in
    api/prompt_examples.json, which the reader learns from."""
    from prompt import parse_prompt
    try:
        lines = Path(log_path).read_text(encoding="utf-8").splitlines()[-last:]
    except OSError:
        return []
    out, seen = [], set()
    for ln in lines:
        try:
            e = json.loads(ln)
        except ValueError:
            continue
        text = (e.get("prompt") or "").strip()
        if not text or text.lower() in seen:
            continue
        seen.add(text.lower())
        claude = e.get("request") or {}
        words = parse_prompt(text, catalog)["request"]
        differ = {k: {"claude": claude.get(k), "word_lists": words.get(k)}
                  for k in ("skill", "class", "ascendancy", "anchor_unique", "anchor_keystone", "anchor_support")
                  if (claude.get(k) or None) != (words.get(k) or None) and words.get(k)}
        if e.get("unused") or differ:
            out.append({"prompt": text, "unused": e.get("unused") or [], "differs": differ, "claude": claude})
    return out
