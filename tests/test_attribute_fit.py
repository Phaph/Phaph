"""Attributes must be met at every stage (A-to-Z sweep 2026-11-18: Int 31 of 40 for 8 blue supports in Act 1;
Loreweave worn at 43 of 45 Int)."""


def test_fit_gems_removes_supports_over_the_colour_total(pob):
    # A level 1 Sorceress has 15 Int; each blue support needs 5 Int, summed over every skill.
    pob.new()
    pob.set_class("Sorceress")
    pob.set_level(1)
    pob.add_skill(["Spark", "Arcane Surge", "Controlled Destruction", "Spell Echo"])
    pob.add_skill(["Frost Bomb", "Elemental Focus", "Considered Casting"], main=False)
    before = pob.calc(["Int", "ReqInt"])
    assert before["ReqInt"] > before["Int"], before
    res = pob.send("fit_gems")
    removed = res.get("removed") or []
    assert removed, res
    after = pob.calc(["Int", "ReqInt"])
    assert after["ReqInt"] <= after["Int"], (after, res)
    # Extra skills give theirs up first: the main skill keeps as many as it can.
    assert removed[0]["skill"] == "Frost Bomb"
