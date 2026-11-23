"""run_guide with leveling: endgame stages build alongside the leveling plan; the swap note lands on the first
endgame stage only when leveling lasts the whole campaign."""
import types


def _fake_build_guide(calls):
    def bg(spec, keys, log=None, progress=None):
        calls.append((tuple(keys), dict(spec.get("leveling") or {})))
        return [types.SimpleNamespace(stage=k, notes=[]) for k in keys]
    return bg


def test_swap_note_on_early_when_leveling_lasts_the_campaign(monkeypatch):
    import api.app as A
    import guide, leveling
    calls = []
    monkeypatch.setenv("LEVELING", "1")
    monkeypatch.setattr(guide, "build_guide", _fake_build_guide(calls))
    monkeypatch.setattr(leveling, "plan_leveling", lambda spec: {"act1": "Spark", "interludes": "Arc", "_why": []})
    monkeypatch.setattr(A, "asdict", lambda g: {"stage": g.stage, "notes": g.notes})
    monkeypatch.setattr(A.writeup, "enabled", lambda: False)
    out = A.run_guide({"spec": {"skill": "Comet"}, "stages": ["act1", "interludes", "early", "end"]})
    assert [s["stage"] for s in out["stages"]] == ["act1", "interludes", "early", "end"]
    early = next(s for s in out["stages"] if s["stage"] == "early")
    assert any("Swap from Arc to Comet" in n for n in early["notes"])
    end_call = next(c for c in calls if "early" in c[0])
    assert end_call[1] == {}          # endgame stages were built without the plan (in parallel)


def test_no_extra_note_when_the_endgame_skill_starts_in_the_campaign(monkeypatch):
    import api.app as A
    import guide, leveling
    monkeypatch.setenv("LEVELING", "1")
    monkeypatch.setattr(guide, "build_guide", _fake_build_guide([]))
    monkeypatch.setattr(leveling, "plan_leveling", lambda spec: {"act1": "Spark", "_why": []})
    monkeypatch.setattr(A, "asdict", lambda g: {"stage": g.stage, "notes": g.notes})
    monkeypatch.setattr(A.writeup, "enabled", lambda: False)
    out = A.run_guide({"spec": {"skill": "Comet"}, "stages": ["act1", "act2", "early"]})
    early = next(s for s in out["stages"] if s["stage"] == "early")
    assert not early["notes"]
