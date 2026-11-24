"""Breaker helpers that need no PoB process."""
import json

from breaker import _can_pair, _top_roll, report


def test_top_roll_takes_the_high_end():
    assert _top_roll("(10-15)% increased Block chance") == "15% increased Block chance"
    assert _top_roll("Adds (1-2) to (4-5) Physical\nDamage") == "Adds 2 to 5 Physical Damage"


def test_one_slot_uniques_do_not_pair():
    ring = {"kind": "unique", "slot": "Ring"}
    helm = {"kind": "unique", "slot": "Helmet"}
    assert _can_pair(ring, dict(ring))
    assert not _can_pair(helm, dict(helm))
    assert _can_pair(helm, {"kind": "keystone"})


def test_report_keeps_only_strong_useful_pairs(tmp_path):
    p = tmp_path / "pairs.json"
    p.write_text(json.dumps({"j": {"skill": "Spark", "ascendancy": "Titan", "pairs": [
        {"a": "A", "ka": "unique", "b": "B", "kb": "keystone", "gain_a": 0.1, "gain_b": 0.1, "gain_ab": 0.5, "synergy": 1.24},
        {"a": "C", "ka": "unique", "b": "D", "kb": "keystone", "gain_a": 0.0, "gain_b": -0.4, "gain_ab": -0.3, "synergy": 1.17},
    ]}}))
    rows = report(p)
    assert [r["a"] for r in rows] == ["A"]


def test_bench_slots_round_trip(pob, monk):
    """A unique tried on the bench replaces the build's item in its slot (clear_slots), then the item comes back."""
    pob.add_item("Rarity: Rare\nTest Gloves\nStocky Mitts\n+80 to maximum Life")
    worn = pob.calc(["Life"])["Life"]
    prev = pob.send("clear_slots", slots=["Gloves"])["prev"]
    assert pob.calc(["Life"])["Life"] < worn
    pob.send("restore_slots", prev=prev)
    assert pob.calc(["Life"])["Life"] == worn


def test_hand_uniques_are_worn_in_the_hand_that_holds_their_kind(pob, monk):
    """A quarterstaff unique replaces the quarterstaff and leaves nothing behind; a caster staff or a bow doesn't fit."""
    import pytest
    from breaker import Bench, pieces
    from pob import PoBError
    ps = {p["name"]: p for p in pieces(pob)}
    hands = [p for p in ps.values() if p.get("raw")]
    assert {"Tangletongue"} <= set(ps) and len(hands) > 50
    pob.add_item("Rarity: RARE\nTest Staff\nWrapped Quarterstaff\nAdds 10 to 20 Physical Damage")
    g = pob.add_skill(["Glacial Cascade"])["group"]
    pob.send("set_main", group=g)
    bench = Bench(pob)
    before = pob.send("equipped")["slots"]["Weapon 1"]["raw"]
    quarter = [p for p in hands if p["slot"] == "Staff" and p.get("subtype") == "Warstaff"]
    caster = [p for p in hands if p["slot"] == "Staff" and p.get("subtype") != "Warstaff"]
    assert quarter and caster
    assert any(abs(bench.gain([p])) > 0.01 for p in quarter)
    for p in (caster[0], ps["Tangletongue"]):
        with pytest.raises(PoBError):
            bench.gain([p])
    assert pob.send("equipped")["slots"]["Weapon 1"]["raw"] == before
    assert abs(bench.gain([])) < 1e-6
