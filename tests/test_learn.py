"""Learning from saved builds: patch labels, bug spotting, head starts, similar builds, prompt misreads."""
import json
import sqlite3
import time

from api import learn
from api.jobs import JobStore
from api.prompt_ai import examples_text
from prompt import parse_prompt

CATALOG = {"classes": [{"name": "Witch", "ascendancies": ["Infernalist", "Lich", "Abyssal Lich"]}],
           "skills": ["Hexblast", "Spark", "Furious Slam"], "uniques": [], "keystones": [], "supports": []}


def _store(tmp_path, patch="0_5"):
    return JobStore(str(tmp_path / "jobs.sqlite3"), workers=1, version="t",
                    runners={}, labels={"game_patch": patch, "pob_version": "0.23", "engine_version": "e"})


def _add(db_path, kind, request, result, patch="0_5"):
    db = sqlite3.connect(db_path)
    db.execute("INSERT INTO jobs (id, cache_key, kind, status, request, result, created, game_patch) "
               "VALUES (?,?,?,?,?,?,?,?)", (str(time.time_ns()), "k", kind, "done", json.dumps(request),
                                            json.dumps(result), time.time(), patch))
    db.commit()


def _search(req, best, others=()):
    ranked = [{"skill": s, "ascendancy": a, "cls": "Witch", "weapon_type": "Staff", "weapon_subtype": None,
               "offhand_type": None, "score": sc, "relative": sc / best[2]} for s, a, sc in [best, *others]]
    return {"result": {"request": req, "best": ranked[0], "ranked": ranked}}


def test_old_database_gets_patch_labels(tmp_path):
    path = tmp_path / "jobs.sqlite3"
    db = sqlite3.connect(path)   # the schema from before labels
    db.execute("CREATE TABLE jobs (id TEXT PRIMARY KEY, cache_key TEXT NOT NULL, kind TEXT NOT NULL, client TEXT, "
               "status TEXT NOT NULL, request TEXT NOT NULL, result TEXT, error TEXT, created REAL NOT NULL, "
               "started REAL, finished REAL)")
    db.execute("INSERT INTO jobs VALUES ('a','k','guide',NULL,'done','{}','{}',NULL,1,1,1)")
    db.commit()
    store = _store(tmp_path)
    row = store.get("a")
    assert row["game_patch"] == "0_5" and row["pob_version"] is None   # old builds: the patch PoB has now
    store.shutdown()


def test_bug_spotting_flags_a_skill_that_wins_too_often(tmp_path):
    store = _store(tmp_path)
    learn.bind(store.db_path, "0_5")
    for i in range(12):
        _add(store.db_path, "generate", {"damage": ["fire" if i % 2 else "cold"]},
             _search({"damage": ["fire" if i % 2 else "cold"]}, ("Hexblast" if i < 9 else "Spark", "Lich", 100.0)))
    _add(store.db_path, "generate", {"skill": "Spark"}, _search({"skill": "Spark"}, ("Spark", "Lich", 100.0)))
    _add(store.db_path, "generate", {}, _search({}, ("Spark", "Lich", 1.0)), patch="0_4")   # other patch: ignored
    w = learn.winners()
    assert w["searches"] == 13 and w["skill"][0] == {"name": "Hexblast", "wins": 9, "share": round(9 / 12, 3)}
    assert any(f["kind"] == "skill" and f["name"] == "Hexblast" for f in w["flags"])
    assert any(f["kind"] == "ascendancy" and f["name"] == "Lich" for f in w["flags"])
    store.shutdown()


def test_head_starts_come_from_similar_searches_on_this_patch(tmp_path):
    store = _store(tmp_path)
    learn.bind(store.db_path, "0_5")
    _add(store.db_path, "generate", {"damage": ["fire"], "kinds": ["spell"]},
         _search({"damage": ["fire"], "kinds": ["spell"]}, ("Hexblast", "Infernalist", 100.0), [("Spark", "Lich", 50.0)]))
    _add(store.db_path, "generate", {"damage": ["cold"]}, _search({"damage": ["cold"]}, ("Spark", "Abyssal Lich", 9.0)))
    _add(store.db_path, "generate", {"damage": ["fire"], "kinds": ["spell"]},
         _search({"damage": ["fire"], "kinds": ["spell"]}, ("Furious Slam", "Lich", 1.0)), patch="0_4")
    heads = learn.head_starts({"damage": ["fire"], "kinds": ["spell"]})
    assert [h["skill"] for h in heads] == ["Hexblast", "Spark"]
    assert learn.head_starts({"damage": ["fire"], "kinds": ["spell"], "ascendancy": "Lich"})[0]["skill"] == "Spark"
    assert learn.head_starts({"damage": ["fire"], "kinds": ["spell"], "random": True}) == []
    # Re-tested seeds from an old patch count too.
    learn._db.execute("INSERT INTO seeds (game_patch, theme, build, score) VALUES (?,?,?,?)",
                      ("0_5", json.dumps({"damage": ["fire"], "kinds": ["spell"]}),
                       json.dumps({"skill": "Furious Slam", "cls": "Witch", "ascendancy": "Lich", "weapon_type": "Staff"}), 5))
    assert "Furious Slam" in [h["skill"] for h in learn.head_starts({"damage": ["fire"], "kinds": ["spell"]})]
    store.shutdown()


def test_similar_builds_for_the_writeup(tmp_path):
    store = _store(tmp_path)
    learn.bind(store.db_path, "0_5")
    guide = lambda skill, asc: {"spec": {"skill": skill, "ascendancy": asc, "weapon_type": "Staff"},
                                "stages": [{"stage": "end", "dps": 1e6, "boss_dps": 2e6, "stats": {"Life": 3000}}]}
    _add(store.db_path, "guide", {}, guide("Hexblast", "Lich"))
    _add(store.db_path, "guide", {}, guide("Spark", "Infernalist"))
    out = learn.similar_builds({"skill": "Hexblast", "ascendancy": "Infernalist", "weapon_type": "Staff"})
    assert {o["skill"] for o in out} == {"Hexblast", "Spark"} and out[0]["mapping_dps"] == 1000000
    store.shutdown()


def test_misreads_and_examples(tmp_path):
    log = tmp_path / "log.jsonl"
    log.write_text(json.dumps({"prompt": "Abyssal Lich build", "request": {"ascendancy": "Lich"}, "unused": []}) + "\n"
                   + json.dumps({"prompt": "spark witch", "request": {"skill": "Spark", "class": "Witch"}, "unused": []}) + "\n")
    out = learn.misreads(log, CATALOG)
    assert [m["prompt"] for m in out] == ["Abyssal Lich build"]
    assert out[0]["differs"]["ascendancy"] == {"claude": "Lich", "word_lists": "Abyssal Lich"}
    text = examples_text(CATALOG)
    assert "Abyssal Lich build" in text and "shaman" not in text.lower()   # Shaman isn't in this catalog: skipped


def test_word_reader_takes_the_longer_ascendancy():
    assert parse_prompt("Abyssal Lich build", CATALOG)["request"]["ascendancy"] == "Abyssal Lich"
    assert parse_prompt("lich hexblast", CATALOG)["request"]["ascendancy"] == "Lich"
