"""Spirit must fit: item-granted spirit skills (The Coming Calamity's heralds) can overdraw it (A-to-Z sweep,
2026-11-18: 17 of 22 Uber Endgame builds reserved 80-120 spirit too much)."""
from gear import SPIRIT_WEIGHT, Scorer


def test_scorer_punishes_overdrawn_spirit():
    score = Scorer(def_weight=0.0, res_weight=0.0)
    base = {"TotalDPS": 1000, "TotalEHP": 1000, "SpiritUnreserved": 10}
    # An item that doubles damage through skills the character can't afford is worse than no change.
    over = {**base, "TotalDPS": 2000, "SpiritUnreserved": -110}
    assert score(over, base) < 0
    assert abs(score({**base, "SpiritUnreserved": -10}, base) + 10 * SPIRIT_WEIGHT) < 1e-9
    # Getting back under the limit is a gain.
    assert score(base, {**base, "SpiritUnreserved": -50}) > 0


def test_fit_spirit_turns_off_granted_heralds(pob):
    calamity = next(u for u in pob.list_uniques() if u["name"].startswith("The Coming Calamity"))
    pob.new()
    pob.set_class("Warrior", "Titan")
    pob.set_level(90)
    pob.add_skill(["Boneshatter"])
    pob.add_item(calamity["raw"])
    pob.send("set_custom_mods", text="-50 to Spirit")   # bare heralds fit 100 spirit; a 50 spirit character can't
    out = pob.calc(["SpiritUnreserved"])
    assert out["SpiritUnreserved"] < 0, "three granted heralds should overdraw 50 spirit"
    res = pob.send("fit_spirit")
    assert res["off"] and all("Herald" in n for n in res["off"])
    assert pob.calc(["SpiritUnreserved"])["SpiritUnreserved"] >= 0
    # Nothing to do when spirit already fits.
    assert pob.send("fit_spirit")["off"] in ([], {})
    pob.send("set_custom_mods", text="")
