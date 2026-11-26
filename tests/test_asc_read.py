"""tools/asc_read.py: outliers between ascendancies, without PoB."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine" / "tools"))
import asc_read  # noqa: E402


def test_outliers():
    row = lambda dps, **g: {"dps": dps, "gains": g, "error": None}
    scans = {a: {"Spark": row(100_000), "Tiny": row(10)} for a in "ABCD"}
    scans["E"] = {"Spark": row(300_000, Cursed=0.4), "Tiny": row(9_000)}
    base, gains = asc_read.outliers(scans)
    assert base[0] == (3.0, "Spark", "E", 300_000, 100_000)
    assert not [r for r in base if r[1] == "Tiny"]          # under the damage floor
    assert gains[0] == (0.4, "Spark", "Cursed", "E", 0.4, 0)
    assert not asc_read.outliers({"A": scans["A"]})[0]      # too few ascendancies to have a median


def test_specific_takes_out_the_usual_effect():
    row = lambda dps, **g: {"dps": dps, "gains": g, "error": None}
    skills = [f"S{i}" for i in range(9)]
    scans = {a: {s: row(100_000) for s in skills} for a in "ABCD"}
    scans["E"] = {s: row(150_000, Cursed=0.5) for s in skills}      # strong on everything: not a finding
    scans["E"]["S0"] = row(300_000, Cursed=0.9)                     # this one is
    base, gains = asc_read.specific(scans)
    assert base[0] == (2.0, "S0", "E", 3.0)
    assert all(abs(r[0] - 1) < 1e-9 for r in base[1:])
    assert gains[0][1:4] == ("S0", "Cursed", "E") and abs(gains[0][0] - 0.4) < 1e-9
    assert all(abs(g[0]) < 1e-9 for g in gains[1:])
