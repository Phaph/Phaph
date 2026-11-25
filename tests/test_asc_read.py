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
