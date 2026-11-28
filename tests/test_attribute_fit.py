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


def test_final_gear_pass_leaves_no_slot_short(pob, monkeypatch):
    """Task 58 (sweep 2026-11-28: Gilded Vestments worn at Str 37 of 46): the final pass's attribute cost is soft, so a
    base it can't wear could stay. Force the body armour pick to the base asking the most Str; the hard check
    must swap it for one the character can wear."""
    import re

    import gear
    from gear import _req_fields, craft_gear, make_stage, own_deficit, SCORE_FIELDS

    real = gear._best_base

    def greedy(pob_, slot, candidates, stage, score):
        if slot != "Body Armour":
            return real(pob_, slot, candidates, stage, score)
        return max(candidates, key=lambda c: (c.get("req") or {}).get("str") or 0 if isinstance(c.get("req"), dict) else 0)["name"]

    monkeypatch.setattr(gear, "_best_base", greedy)
    # No attribute affixes either, so the soft cost can't buy the attribute back on other slots.
    fill = gear._fill
    no_attr = lambda g: re.search("Strength|Dexterity|Intelligence|Attribute", g) is None
    monkeypatch.setattr(gear, "_fill", lambda p, w, st, sc, lim, allow: fill(p, w, st, sc, lim, lambda g: allow(g) and no_attr(g)))
    st = make_stage("interludes")
    pob.new()
    pob.set_class("Sorceress", "Stormweaver")
    pob.set_level(st.level)
    pob.add_skill(["Spark"])
    craft_gear(pob, st, "Wand", None, uniques=False, log=lambda *a: None, attr_weight=0.25)
    for slot in ("Weapon 1", "Weapon 2", "Helmet", "Body Armour", "Gloves", "Boots", "Amulet", "Ring 1", "Ring 2", "Belt"):
        out = pob.calc(SCORE_FIELDS + _req_fields(slot))
        assert own_deficit(out, slot) <= 0, (slot, {k: out.get(k) for k in ("Str", "Dex", "Int", *_req_fields(slot))})
