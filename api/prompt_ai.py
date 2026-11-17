"""Claude reads the player's prompt (POST /parse with "ai": true).

The word lists in engine/prompt.py read clear prompts well but miss anything phrased their own way ("I want to
punch things", "a necromancer like in Diablo"). Here Claude reads the prompt instead and fills in the same request
the engine takes. It gets the real names (skills, uniques, keystones, supports, classes) and may only answer with
them: every name is checked again here, and anything unknown is dropped and reported, so Claude can't invent an item.

Without ANTHROPIC_API_KEY (or if the call fails) the caller falls back to the word-list reader, so the site never
depends on the API being up. Every reading is appended to /data/prompt_log.jsonl (prompt text and result, nothing
about the player) so misreads can be found and fixed: that log is how this gets better over time.
"""
from __future__ import annotations

import json
import os
import threading
import time
from collections import OrderedDict
from pathlib import Path

MODEL = os.environ.get("PROMPT_MODEL", "claude-opus-5-5")
LOG = Path(os.environ.get("PROMPT_LOG", "/data/prompt_log.jsonl"))
CACHE_SIZE = 500
_cache: OrderedDict[str, dict] = OrderedDict()
_lock = threading.Lock()
_client = None

INSTRUCTIONS = """You read Path of Exile 2 build requests for a build planner and turn each into a search request.

The player types what they want, in their own words. Fill in only what they asked for; leave everything else empty.
The planner picks the best of everything left open, so an empty field is better than a guess.

Rules:
- Use only names from the lists below, spelled exactly as listed. If the player names something not in a list,
  leave it out and put the words in "unused".
- "skill": the one damage skill the build should use, only if the player named one (or clearly described one, e.g.
  "throw fireballs" is Fireball). Skills that boost others (Cast on X, auras, heralds, buffs) go in "with_skills".
- "anchor_unique" / "anchor_keystone" / "anchor_support": the one item, keystone or support gem the build is
  made around, only if the player names it or asks for a build around it.
- "kinds", "damage", "ailment", "weapons", "goals", "avoid", "mode", "budget": from the allowed values only.
- "weapons" is the main weapon. If the player names a second weapon ("crossbow build with a mace", "bow and spear"),
  the first is "weapons" and the second "second_weapons" (it goes on weapon set 2). Never more than two.
  "avoid" is for things the player said no to ("no minions" -> kinds "minion" in avoid).
- "off_meta": true when the player wants something unusual, unpopular, creative or not the meta.
- "random": true only when the player asks for a random or surprise build.
- "deep": true when the player wants the strongest build there is, whatever it takes.
- "class" / "ascendancy": only if named. A description is not a name: "necromancer" means kinds ["minion"] (and
  class Witch if they want a witch), not a guessed ascendancy.
- "found": for each thing you filled in, the player's words and what you took them to mean, in plain English.
- "unused": words you could not use.
"""


def _client_or_none():
    global _client
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    if _client is None:
        import anthropic
        _client = anthropic.Anthropic(timeout=20.0, max_retries=1)
    return _client


def available() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _schema(catalog: dict, tables: dict) -> dict:
    s = lambda: {"type": "string"}
    # Short lists are enums. Long name lists (hundreds of skills and uniques) are plain strings: they are in the
    # system prompt, and _clean drops any name that isn't real.
    strs = lambda values=None: {"type": "array", "items": {"type": "string", **({"enum": sorted(values)} if values else {})}}
    one = lambda values=None: {"anyOf": [{"type": "string", **({"enum": sorted(values)} if values else {})}, {"type": "null"}]}
    classes = [c["name"] for c in catalog["classes"]]
    ascs = [a for c in catalog["classes"] for a in c["ascendancies"]]
    props = {
        "skill": one(),
        "with_skills": strs(),
        "anchor_unique": one(),
        "anchor_keystone": one(catalog.get("keystones") or None),
        "anchor_support": one(),
        "class": one(classes),
        "ascendancy": one(ascs),
        "damage": strs(tables["damage"]),
        "kinds": strs(tables["kinds"]),
        "ailment": one(tables["ailments"]),
        "weapons": strs(list(catalog["weapon_types"])),
        "second_weapons": strs(list(catalog["weapon_types"])),
        "goals": strs(tables["goals"]),
        "with_types": strs(tables["helper_kinds"]),
        "avoid": strs(tables["damage"] | tables["kinds"]),
        "mode": one({"balanced", "mapping", "bossing"}),
        "budget": one({b["key"] for b in catalog["budgets"]}),
        "off_meta": {"type": "boolean"},
        "random": {"type": "boolean"},
        "deep": {"type": "boolean"},
        "found": {"type": "array", "items": {"type": "object", "properties": {"text": s(), "means": s()},
                                             "required": ["text", "means"], "additionalProperties": False}},
        "unused": {"type": "array", "items": s()},
    }
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


def engine_tables() -> dict:
    """The allowed words for each field, from the engine's own tables (so the two readers agree)."""
    from generate import HELPER_TYPES, KIND_TYPES
    from goals import GOAL_LABELS
    from prompt import DAMAGE
    return {"damage": set(DAMAGE.values()), "kinds": set(KIND_TYPES), "goals": set(GOAL_LABELS),
            "helper_kinds": set(HELPER_TYPES), "ailments": {"bleed", "poison", "ignite", "shock", "chill", "freeze"}}


def _system(catalog: dict) -> str:
    """The instructions plus every name: the same for every prompt, so it is cached."""
    lists = {
        "Damage skills and other active skills": catalog["skills"],
        "Skills that boost others (go in with_skills)": catalog.get("helper_skills") or [],
        "Uniques": catalog.get("uniques") or [],
        "Keystones": catalog.get("keystones") or [],
        "Support gems": catalog.get("supports") or [],
        "Classes and ascendancies": [f"{c['name']}: {', '.join(c['ascendancies'])}" for c in catalog["classes"]],
    }
    return INSTRUCTIONS + "\n" + "\n".join(f"\n{k}:\n" + "; ".join(v) for k, v in lists.items())


def _clean(out: dict, catalog: dict, tables: dict) -> dict:
    """Keep only real names and allowed values (the schema should already ensure this; this is the backstop)."""
    known = {
        "skill": set(catalog["skills"]), "anchor_unique": set(catalog.get("uniques") or []),
        "anchor_keystone": set(catalog.get("keystones") or []), "anchor_support": set(catalog.get("supports") or []),
        "class": {c["name"] for c in catalog["classes"]},
        "ascendancy": {a for c in catalog["classes"] for a in c["ascendancies"]},
        "ailment": tables["ailments"], "mode": {"balanced", "mapping", "bossing"},
        "budget": {b["key"] for b in catalog["budgets"]},
    }
    lists = {"with_skills": set(catalog["skills"]), "damage": tables["damage"], "kinds": tables["kinds"],
             "weapons": set(catalog["weapon_types"]), "second_weapons": set(catalog["weapon_types"]), "goals": tables["goals"], "with_types": tables["helper_kinds"],
             "avoid": tables["damage"] | tables["kinds"]}
    req: dict = {"damage": [], "kinds": [], "weapons": [], "goals": []}
    dropped = []
    for k, allowed in known.items():
        v = out.get(k)
        if v in allowed:
            req[k] = v
        elif v:
            dropped.append(str(v))
    for k, allowed in lists.items():
        vals = [v for v in out.get(k) or [] if v in allowed]
        dropped += [v for v in out.get(k) or [] if v not in allowed]
        if vals or k in req:
            req[k] = vals[:8 if k == "goals" else 5 if k in ("damage", "kinds", "weapons", "second_weapons", "avoid") else 3]
    for k in ("off_meta", "random", "deep"):
        if out.get(k):
            req[k] = True
    if req.get("ascendancy") and not req.get("class"):
        req["class"] = next(c["name"] for c in catalog["classes"] if req["ascendancy"] in c["ascendancies"])
    return {"request": req, "found": [f for f in out.get("found") or [] if f.get("text") and f.get("means")],
            "budget_set": "budget" in req, "unused": [*(out.get("unused") or []), *dropped], "reader": "claude"}


def read_prompt(text: str, catalog: dict) -> dict | None:
    """Claude's reading of the prompt in the /parse shape, or None (no key, refusal, error: use the word lists)."""
    client = _client_or_none()
    if client is None or not text.strip():
        return None
    key = text.strip().lower()
    with _lock:
        if key in _cache:
            _cache.move_to_end(key)
            return _cache[key]
    import anthropic
    tables = engine_tables()
    t0 = time.time()
    try:
        resp = client.beta.messages.create(
            model=MODEL,
            max_tokens=4000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",   # a safety decline is retried on a fallback model in the same call
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": _schema(catalog, tables)}},
            system=[{"type": "text", "text": _system(catalog), "cache_control": {"type": "ephemeral", "ttl": "1h"}}],
            messages=[{"role": "user", "content": text[:500]}],
        )
    except (anthropic.APIConnectionError, anthropic.RateLimitError, anthropic.APIStatusError):
        return None
    if resp.stop_reason != "end_turn":
        return None   # refusal or cut off: the word lists read it instead
    body = next((b.text for b in resp.content if b.type == "text"), "")
    try:
        result = _clean(json.loads(body), catalog, tables)
    except (ValueError, TypeError, StopIteration):
        return None
    _log(text, result, time.time() - t0, resp.usage)
    with _lock:
        _cache[key] = result
        while len(_cache) > CACHE_SIZE:
            _cache.popitem(last=False)
    return result


def _log(text: str, result: dict, seconds: float, usage) -> None:
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"t": int(time.time()), "prompt": text, "request": result["request"],
                                "unused": result["unused"], "seconds": round(seconds, 2),
                                "cache_read": getattr(usage, "cache_read_input_tokens", None),
                                "input": getattr(usage, "input_tokens", None),
                                "output": getattr(usage, "output_tokens", None)}) + "\n")
    except OSError:
        pass
