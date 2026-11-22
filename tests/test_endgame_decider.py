"""Endgame-first pick (generate.endgame_decider): the search's top skills are built at Uber Endgame and the best
one moves to the top (Kyle 2026-11-22)."""
import types

import generate as g


def _row(skill, score):
    return {"skill": skill, "ascendancy": "Deadeye", "cls": "Ranger", "weapon_type": "Bow", "weapon_subtype": None,
            "offhand_type": None, "score": score, "dps": score, "boss": score}


def test_decider_moves_the_endgame_winner_up(monkeypatch):
    end = {"Rain of Arrows": 650_000, "Ice Shot": 1_150_000, "Electrocuting Arrow": 900_000}
    import guide
    monkeypatch.setattr(guide, "build_stage", lambda spec, key: types.SimpleNamespace(
        boss_dps=end[spec["skill"]], dps=end[spec["skill"]], stats={}))
    result = {"ranked": [_row("Rain of Arrows", 3), _row("Ice Shot", 2), _row("Electrocuting Arrow", 1)],
              "request": {}, "best": _row("Rain of Arrows", 3)}
    out = g.endgame_decider(result, log=lambda *a: None)
    assert out["ranked"][0]["skill"] == "Ice Shot"
    assert out["decider"]["changed"] and [f["skill"] for f in out["decider"]["finalists"]][0] == "Ice Shot"
    assert g.plan_build(out)["spec"]["skill"] == "Ice Shot"


def test_decider_keeps_the_order_when_the_search_was_right(monkeypatch):
    import guide
    monkeypatch.setattr(guide, "build_stage", lambda spec, key: types.SimpleNamespace(
        boss_dps={"A": 3, "B": 2}[spec["skill"]] * 1e6, dps=1e6, stats={}))
    result = {"ranked": [_row("A", 2), _row("B", 1)], "request": {}}
    out = g.endgame_decider(result, log=lambda *a: None)
    assert out["ranked"][0]["skill"] == "A" and not out["decider"]["changed"]


def test_guide_reuses_the_winners_uber_stage(monkeypatch):
    import guide
    calls = []
    fake = types.SimpleNamespace(boss_dps=2e6, dps=2e6, stats={})
    monkeypatch.setattr(guide, "build_stage", lambda spec, key, *a: (calls.append((spec["skill"], key)), fake)[1])
    result = {"ranked": [_row("A", 2), _row("B", 1)], "request": {}}
    out = g.endgame_decider(result, light=False, log=lambda *a: None)
    spec = g.plan_build(out)["spec"]
    monkeypatch.setattr(guide, "asdict", lambda x: {}, raising=False)
    n = len(calls)
    guides = guide.build_guide(spec, ["end"], log=lambda *a: None)
    assert len(calls) == n and guides[0] is fake      # not built again
