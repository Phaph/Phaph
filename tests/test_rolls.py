"""Task 57: uniques with random choices (Mageblood) worn with a typical roll when gear.TYPICAL_ROLLS is on."""
import gear


def _mageblood(pob):
    return next(u for u in pob.list_uniques() if u["name"].startswith("Mageblood"))


def test_typical_roll_is_worse_than_best_and_lists_the_hunt(pob, monkeypatch):
    pob.new()
    pob.set_class("Sorceress", None)
    pob.set_level(80)
    pob.add_skill(["Spark"])
    score = gear.Scorer(mode="bossing")
    base = pob.calc(gear.SCORE_FIELDS)
    raw = _mageblood(pob)["raw"]
    monkeypatch.setattr(gear, "TYPICAL_ROLLS", False)
    best = gear.best_variants(pob, raw, "Belt", score)
    assert best not in gear.HUNT
    monkeypatch.setattr(gear, "TYPICAL_ROLLS", True)
    typical = gear.best_variants(pob, raw, "Belt", score)
    hunt = gear.HUNT[typical]
    assert len(hunt) == 4 and len(set(hunt)) == 4 and all(h.startswith("Legacy of ") for h in hunt)
    outs = gear._try(pob, "Belt", [best, typical])
    assert score(outs[0], base) > score(outs[1], base)
