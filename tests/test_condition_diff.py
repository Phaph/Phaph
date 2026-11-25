"""Launch-day damage diff (condition_scan.diff): number changes the wording diff can't see."""
import condition_scan


def _scan(code, **dps):
    return {"code": code, "skills": {n: {"dps": v, "error": None, "gains": {}} for n, v in dps.items()}}


def test_moves_new_and_gone_skills_are_listed():
    out = condition_scan.diff(_scan("x", Arc=100, Comet=100, Spark=100), _scan("x", Arc=120, Comet=102, Rend=50))
    assert "WARNING" not in out
    assert "1 of 2 skills moved" in out and "+20%" in out and "Comet" not in out
    assert "New (or worked only now): Rend" in out and "Gone (or broken now): Spark" in out


def test_different_or_unknown_engine_code_is_called_out():
    assert "WARNING" in condition_scan.diff(_scan("x", Arc=100), _scan("y", Arc=100))
    assert "WARNING" in condition_scan.diff(_scan(None, Arc=100), _scan(None, Arc=100))
