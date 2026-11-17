"""Claude writes a short overview of each finished build (like the "Build Overview" on a Mobalytics guide).

It gets the endgame stage's real data (skills and what each one is for, supports, uniques, key passives, damage,
defences, spirit, the conditions assumed, the engine's notes) and writes from those facts only: how the build works,
its key items and why, and which stats to chase. It runs once when a guide is made and is stored with it, so a shared
or cached build costs nothing more. Without ANTHROPIC_API_KEY, or if the call fails, the guide simply has no overview.
"""
from __future__ import annotations

import json
import os

from . import prompt_ai

INSTRUCTIONS = """You write the short overview at the top of a Path of Exile 2 build guide, for players.

You get the build's real data from Path of Building. Write only from those facts: never add a skill, item, passive,
mechanic or number that isn't in the data. Plain, friendly English; short sentences; no hype words.

- "overview": 1-2 sentences: what the build is and how it kills things.
- "how_it_works": 4-6 bullets. How the main skills, supports, buffs, uniques and passives work together, and how the
  build stays alive. Name the gems and items exactly as written in the data.
- "key_items": the build's uniques (and any item that matters), each with one line on why. Empty if none.
- "stat_priority": 4-7 stats to look for on gear, most important first, based on what the build scales.
- "playstyle": one sentence on how to play it (what to press when mapping and when bossing).
Wrap every gem, item and passive name in [[double brackets]], e.g. [[Hexblast]], so the page can show its icon.
"""

SCHEMA = {
    "type": "object",
    "properties": {
        "overview": {"type": "string"},
        "how_it_works": {"type": "array", "items": {"type": "string"}},
        "key_items": {"type": "array", "items": {"type": "object", "properties": {
            "name": {"type": "string"}, "why": {"type": "string"}}, "required": ["name", "why"],
            "additionalProperties": False}},
        "stat_priority": {"type": "array", "items": {"type": "string"}},
        "playstyle": {"type": "string"},
    },
    "required": ["overview", "how_it_works", "key_items", "stat_priority", "playstyle"],
    "additionalProperties": False,
}

STAT_KEYS = ["Life", "EnergyShield", "Mana", "Spirit", "TotalEHP", "Armour", "Evasion", "BlockChance", "CritChance",
             "Speed", "FireResist", "ColdResist", "LightningResist", "ChaosResist", "MovementSpeedMod", "Str", "Dex", "Int"]


def facts(spec: dict, stages: list[dict]) -> dict:
    """The endgame stage, boiled down to what a player needs to understand the build."""
    end = next((s for s in stages if s.get("stage") == "end"), stages[-1] if stages else {})
    st = end.get("stats") or {}
    skills = [{"skill": spec.get("skill"), "role": "main (mapping)", "supports": end.get("supports") or []}]
    if end.get("clear_skill"):
        skills.append({"skill": end["clear_skill"], "role": "clearing", "supports": end.get("clear_supports") or []})
    if end.get("boss_skill"):
        skills.append({"skill": end["boss_skill"], "role": "bossing", "supports": end.get("boss_supports") or []})
    elif end.get("boss_supports"):
        skills.append({"skill": spec.get("skill"), "role": "bossing (support swap)", "supports": end["boss_supports"]})
    if end.get("trigger"):
        t = end["trigger"]
        skills.append({"skill": t.get("spell"), "role": f"triggered by {t.get('gem')}", "supports": t.get("supports") or []})
    for x in end.get("setups") or []:
        skills.append({"skill": x.get("skill"), "role": x.get("role"), "supports": x.get("supports") or []})
    gear = [{"slot": g.get("slot"), "unique": (g.get("unique") or "").split(",")[0]} for g in end.get("gear") or []
            if g.get("unique")]
    return {
        "class": spec.get("class"), "ascendancy": spec.get("ascendancy"), "weapon": spec.get("weapon_type"),
        "offhand": spec.get("offhand_type"), "budget": spec.get("budget"), "goals": spec.get("goals") or [],
        "built_around": [spec[k] for k in ("anchor_unique", "anchor_keystone", "anchor_support") if spec.get(k)],
        "skills": skills, "uniques": gear,
        "key_passives": [p.get("name") for p in end.get("tree_order") or [] if p.get("type") in ("Notable", "Keystone")][:12],
        "ascendancy_passives": [p.get("name") for p in end.get("tree_order") or [] if p.get("ascendancy")],
        "mapping_dps": round(end.get("dps") or 0), "boss_dps": round(end.get("boss_dps") or 0),
        "damage_split": end.get("damage_split") or {},
        "stats": {k: round(st[k], 1) for k in STAT_KEYS if isinstance(st.get(k), (int, float))},
        "assumed": [c.get("why") for c in end.get("conditions") or []][:8],
        "notes": (end.get("notes") or [])[:10],
    }


def write_up(spec: dict, stages: list[dict]) -> dict | None:
    """Claude's overview for a finished guide, or None (no key, refusal, error)."""
    client = prompt_ai._client_or_none()
    if client is None or not stages:
        return None
    import anthropic
    try:
        resp = client.beta.messages.create(
            model=prompt_ai.MODEL,
            max_tokens=6000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
            system=INSTRUCTIONS,
            messages=[{"role": "user", "content": json.dumps(facts(spec, stages), ensure_ascii=False)}],
        )
    except (anthropic.APIConnectionError, anthropic.RateLimitError, anthropic.APIStatusError):
        return None
    if resp.stop_reason != "end_turn":
        return None
    body = next((b.text for b in resp.content if b.type == "text"), "")
    try:
        out = json.loads(body)
    except ValueError:
        return None
    out["by"] = "claude"
    return out


def enabled() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY")) and os.environ.get("WRITEUPS", "1") != "0"
