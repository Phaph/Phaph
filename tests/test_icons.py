"""Icon link harvesting. No network: synthetic data in poe.ninja's shapes."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine" / "tools"))
from fetch_icons import _column, harvest_character  # noqa: E402

CDN = "https://web.poecdn.com/gen/image/x/y/"


def _col(name, values):
    out = b"\n" + bytes([len(name)]) + name.encode() + b"\x12" + bytes([len(name)]) + name.encode() + b" \x01"
    for v in values:
        out += b":" + bytes([len(v)]) + v.encode()
    return out


def test_column_reader():
    blob = b"junk" + _col("account", ["a-0001", "b-0002"]) + b"Z\x00" + _col("name", ["Alice", "Bob"]) + b"R\x03end"
    assert _column(blob, "account") == ["a-0001", "b-0002"]
    assert _column(blob, "name") == ["Alice", "Bob"]
    assert _column(blob, "missing") == []


def test_harvest_character():
    icons = {"uniques": {}, "bases": {}, "gems": {}}
    data = {
        "items": [{"itemData": {"frameType": 2, "baseType": "Soaring Spear", "icon": CDN + "spear.png"}},
                  {"itemData": {"frameType": 3, "name": "Headhunter", "baseType": "Heavy Belt", "icon": CDN + "hh.png"}},
                  {"itemData": {"frameType": 2, "baseType": "Bad", "icon": "https://elsewhere.example/x.png"}}],
        "skills": [{"allGems": [{"name": "Arc", "itemData": {"icon": CDN + "arc.png"}}]}],
    }
    harvest_character(data, icons)
    assert icons["bases"] == {"Soaring Spear": CDN + "spear.png"}
    assert icons["uniques"] == {"Headhunter": CDN + "hh.png"}
    assert icons["gems"] == {"Arc": CDN + "arc.png"}
