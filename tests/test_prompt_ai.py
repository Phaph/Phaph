"""Claude prompt reader: names are checked, nothing made up gets through, and no key means the word lists."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))
import prompt_ai  # noqa: E402

CATALOG = {
    "classes": [{"name": "Witch", "ascendancies": ["Infernalist", "Lich"]}],
    "skills": ["Spark", "Fireball", "Raise Zombie"],
    "helper_skills": ["Herald of Ice"],
    "uniques": ["Kalandra's Touch"],
    "keystones": ["Chaos Inoculation"],
    "supports": ["Brutality II"],
    "weapon_types": {"Wand": [], "Staff": []},
}


def tables():
    return {"damage": {"fire", "lightning"}, "kinds": {"minion", "spell"}, "goals": {"es", "tanky"},
            "helper_kinds": {"aura"}, "ailments": {"ignite"}}


def test_clean_keeps_real_names_and_drops_made_up_ones():
    out = {"skill": "Spark", "anchor_unique": "Mageblood of Doom", "anchor_keystone": "Chaos Inoculation",
           "ascendancy": "Lich", "class": None, "damage": ["lightning", "plasma"], "kinds": [], "weapons": ["Wand"],
           "goals": ["es"], "off_meta": True, "random": False, "found": [{"text": "ci", "means": "Chaos Inoculation"}],
           "unused": ["zappy"]}
    r = prompt_ai._clean(out, CATALOG, tables())
    req = r["request"]
    assert req["skill"] == "Spark" and req["anchor_keystone"] == "Chaos Inoculation"
    assert "anchor_unique" not in req and req["damage"] == ["lightning"]
    assert req["class"] == "Witch"   # the ascendancy sets its class
    assert req["off_meta"] is True and "random" not in req
    assert "Mageblood of Doom" in r["unused"] and "plasma" in r["unused"] and r["reader"] == "claude"


def test_schema_is_strict():
    s = prompt_ai._schema(CATALOG, tables())
    assert s["additionalProperties"] is False and set(s["required"]) == set(s["properties"])


def test_no_key_means_word_lists(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(prompt_ai, "_client", None)
    assert prompt_ai.read_prompt("spark witch", CATALOG) is None


def test_reads_through_a_client(monkeypatch, tmp_path):
    pytest = __import__("pytest")
    pytest.importorskip("anthropic")
    body = {"skill": "Fireball", "damage": ["fire"], "found": [{"text": "throw fireballs", "means": "Skill: Fireball"}],
            "unused": []}
    calls = []

    class Messages:
        def create(self, **kw):
            calls.append(kw)
            return SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text=json.dumps(body))],
                                   usage=SimpleNamespace(cache_read_input_tokens=0, input_tokens=10, output_tokens=5))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setattr(prompt_ai, "_client", SimpleNamespace(beta=SimpleNamespace(messages=Messages())))
    monkeypatch.setattr(prompt_ai, "engine_tables", tables)
    monkeypatch.setattr(prompt_ai, "LOG", tmp_path / "log.jsonl")
    prompt_ai._cache.clear()
    r = prompt_ai.read_prompt("I want to throw fireballs", CATALOG)
    assert r["request"]["skill"] == "Fireball" and r["request"]["damage"] == ["fire"]
    assert prompt_ai.read_prompt("i want to throw fireballs", CATALOG) is r   # cached
    assert len(calls) == 1 and calls[0]["model"] == prompt_ai.MODEL
    assert (tmp_path / "log.jsonl").read_text().count("\n") == 1


def test_writeup_facts_come_from_the_build():
    from api.writeup import facts
    spec = {"class": "Witch", "ascendancy": "Blood Mage", "skill": "Hexblast", "weapon_type": "Staff",
            "anchor_keystone": "Chaos Inoculation"}
    end = {"stage": "end", "supports": ["Deliberation"], "boss_supports": ["Fiery Death"], "dps": 9.4e6,
           "setups": [{"skill": "Life Remnants", "role": "granted", "supports": ["Remnant Potency III"]}],
           "gear": [{"slot": "Belt", "unique": "Mageblood, Heavy Belt"}, {"slot": "Ring 1", "unique": None}],
           "tree_order": [{"name": "Pure Chaos", "type": "Notable"}, {"name": "Gore Spike", "type": "Notable", "ascendancy": True}],
           "stats": {"Life": 3300.4, "Spirit": 100}}
    f = facts(spec, [{"stage": "early"}, end])
    assert [s["role"] for s in f["skills"]] == ["main (mapping)", "bossing (support swap)", "granted"]
    assert f["uniques"] == [{"slot": "Belt", "unique": "Mageblood"}] and f["built_around"] == ["Chaos Inoculation"]
    assert f["ascendancy_passives"] == ["Gore Spike"] and f["stats"]["Life"] == 3300.4 and f["mapping_dps"] == 9400000
