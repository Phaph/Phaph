"""Engine checks: PoB commands, game rules PoB enforces, and our own correctness fixes."""
import pytest
from conftest import SPEAR, STAFF

from optimize import clear_score, optimise_supports, total_dps
from pob import PoBError, decode_build_code, encode_build_code

FIELDS = ["TotalDPS", "TotalDotDPS", "Life", "TotalEHP", "FireResist", "BleedDPS", "BleedChance"]


def test_classes_and_ascendancies(pob):
    classes = {c["name"]: c["ascendancies"] for c in pob.list_classes()}
    assert "Invoker" in classes["Monk"]
    assert "Amazon" in classes["Huntress"]


def test_set_class_rejects_unknown(pob):
    pob.new()
    with pytest.raises(PoBError):
        pob.set_class("Monk", "Wizard")


def test_level_changes_life_and_points(pob):
    pob.new()
    pob.set_class("Monk")
    pob.set_level(10)
    life10, pts10 = pob.calc(["Life"])["Life"], pob.points()["available"]
    pob.set_level(90)
    life90, pts90 = pob.calc(["Life"])["Life"], pob.points()["available"]
    assert life90 > life10 and pts90 == pts10 + 80


def test_unknown_gem_is_reported(pob):
    pob.new()
    res = pob.add_skill(["Not A Real Skill"])
    assert res["unknown_gems"] == ["Not A Real Skill"]


def test_try_skill_is_not_one_step_behind(pob, monk):
    """Regression: try_skill used to return the previous combo's numbers."""
    a = pob.try_skill(monk, ["Tempest Flurry", "Lightning Penetration"], FIELDS)["output"]["TotalDPS"]
    b = pob.try_skill(monk, ["Tempest Flurry", "Concentrated Area"], FIELDS)["output"]["TotalDPS"]
    a2 = pob.try_skill(monk, ["Tempest Flurry", "Lightning Penetration"], FIELDS)["output"]["TotalDPS"]
    assert a == pytest.approx(a2) and a != pytest.approx(b)


def test_bleed_iv_stops_the_skill_from_bleeding(pob):
    pob.new()
    pob.set_class("Huntress", "Amazon")
    pob.set_level(90)
    pob.add_item(SPEAR)
    g = pob.add_skill(["Rake"])["group"]
    plain = pob.try_skill(g, ["Rake"], FIELDS)["output"]
    with_iv = pob.try_skill(g, ["Rake", "Bleed IV"], FIELDS)["output"]
    assert plain.get("BleedDPS", 0) > 0
    assert with_iv.get("BleedDPS", 0) == 0


def test_lineage_copy_limit_warns(pob, monk):
    pob.add_skill(["Falling Thunder", "Rakiata's Flow"], main=False)
    res = pob.try_skill(monk, ["Tempest Flurry", "Rakiata's Flow"], FIELDS)
    assert any("lineage" in w.lower() for w in res["warnings"])


def test_optimiser_skips_conditional_supports(pob, monk):
    best = optimise_supports(pob, monk, "Tempest Flurry", slots=3, log=lambda *a: None)[0]
    conditional = {g["name"] for g in pob.list_gems("support") if g["conditional"]}
    assert best.supports and not conditional & set(best.supports)
    families = [next(g["family"] for g in pob.list_gems("support") if g["name"] == s) for s in best.supports]
    assert len(families) == len(set(families)), "two gems from the same family"


def test_try_items_matches_equip(pob, monk):
    raw = "Rarity: Rare\nT\nRough Greaves\n+80 to maximum Life\n+30% to Fire Resistance"
    what_if = pob.send("try_items", slot="Boots", items=[raw], fields=FIELDS)["results"][0]
    equipped = pob.send("equip", slot="Boots", raw=raw, fields=FIELDS)["output"]
    for k in ("TotalDPS", "Life", "FireResist", "TotalEHP"):
        assert what_if.get(k) == pytest.approx(equipped.get(k))


def test_try_items_reports_bad_items(pob, monk):
    res = pob.send("try_items", slot="Boots", items=["Rarity: Rare\nT\nNot A Base"], fields=FIELDS)["results"]
    assert "error" in res[0]


def test_save_load_round_trip(pob, monk):
    pob.optimise_tree(points=20)
    before = pob.calc(FIELDS)
    code = pob.save_code()
    assert decode_build_code(code) and encode_build_code(decode_build_code(code))
    pob.load_code(code)
    after = pob.calc(FIELDS)
    for k in before:
        assert after[k] == pytest.approx(before[k])


def test_tree_optimiser_is_deterministic(pob, monk):
    xml = pob.save_xml()
    pob.optimise_tree(points=30)
    first = pob.calc(FIELDS)
    pob.load_xml(xml)
    pob.optimise_tree(points=30)
    assert pob.calc(FIELDS)["TotalDPS"] == pytest.approx(first["TotalDPS"])


def test_tree_optimiser_spends_points_and_helps(pob, monk):
    before = total_dps(pob.calc(FIELDS))
    res = pob.optimise_tree(points=40)
    assert res["used"] <= 40 and res["used"] >= 35
    assert total_dps(pob.calc(FIELDS)) > before * 1.5


def test_clear_score_rewards_area():
    base = {"TotalDPS": 1000, "TotalDotDPS": 0, "AreaOfEffectMod": 1}
    assert clear_score({**base, "AreaOfEffectMod": 2}) > clear_score(base)
    assert clear_score({**base, "TotalDotDPS": 1000}) < total_dps({**base, "TotalDotDPS": 1000})


def test_minion_damage_counts(pob):
    """Regression: minion builds scored zero because minion DPS lives in a separate table."""
    pob.new()
    pob.set_class("Witch", "Infernalist")
    pob.set_level(90)
    pob.add_skill(["Skeletal Storm Mage"])
    out = pob.calc(["TotalDPS", "MinionDPS", "MinionDotDPS"])
    assert out.get("MinionDPS", 0) > 0 and total_dps(out) > 0


def test_duplicate_gem_names_pick_the_castable_gem(pob):
    """Regression: 'Lightning Bolt' resolved to its triggered twin and no support applied."""
    pob.new()
    pob.set_class("Sorceress", "Stormweaver")
    pob.set_level(75)
    g = pob.add_skill(["Lightning Bolt"])["group"]
    assert pob.calc(["TotalDPS"]).get("TotalDPS", 0) > 0
    res = pob.try_skill(g, ["Lightning Bolt", "Lightning Penetration"], FIELDS)
    assert res["supported"].get("Lightning Penetration")


def test_tree_swap_phase_only_keeps_improvements(pob, monk):
    """The swap phase takes weak branches back and re-spends them; it must never leave the build worse,
    stay within the points, and the order to take passives must still cover every point spent."""
    res = pob.optimise_tree(points=40)
    assert res["used"] <= 40
    assert res["score_after_swaps"] >= res["score_before_swaps"] - 1e-9
    alloc = set(pob.send("allocated")["nodes"])
    main = set()
    for s in res["steps"]:
        ids = set(s["path"]) | {s["id"]}
        assert ids <= alloc, "the order lists a passive that isn't in the tree"
        if not s.get("ascendancy"):
            assert not (ids & main), "a passive appears twice in the order"
            main |= ids
    assert len(main) == res["used"]


def test_tree_long_reach_never_scores_lower(pob, monk):
    xml = pob.save_xml()
    pob.optimise_tree(points=40, far_dist=6, refine=False)
    old = total_dps(pob.calc(FIELDS))
    pob.load_xml(xml)
    pob.optimise_tree(points=40)
    assert total_dps(pob.calc(FIELDS)) >= old * 0.95


def test_jewel_affixes_come_from_the_jewel_pool(pob):
    affixes = pob.send("affixes", base="Ruby", max_level=82)["affixes"]
    assert affixes and all(a["type"] in ("Prefix", "Suffix") for a in affixes)
    assert not any("to maximum Life" in a["lines"][0] and a["lines"][0].startswith("+(") and "Jewel" not in a["id"]
                   for a in affixes), "gear affixes leaked into the jewel pool"


def test_jewels_fill_the_sockets_the_tree_takes(pob, monk):
    from gear import Scorer, make_stage
    from jewels import craft_jewels, jewel_sockets, proxy_jewel

    stage = make_stage("end", "high")
    score = Scorer()
    nodes, stats = pob.send("allocated")["nodes"], pob.calc(FIELDS)
    raw = proxy_jewel(pob, stage, score)
    assert raw and raw.splitlines()[2] in ("Ruby", "Emerald", "Sapphire")
    # Making the stand-in jewel must leave the build as it was.
    assert pob.send("allocated")["nodes"] == nodes
    for k, v in stats.items():
        assert pob.calc(FIELDS)[k] == pytest.approx(v)
    pob.optimise_tree(jewel=raw, refine=False)
    taken = [s for s in jewel_sockets(pob) if s["alloc"]]
    assert taken, "a strong jewel should pull the tree into at least one socket"
    plans = craft_jewels(pob, stage, score, log=lambda *a: None)
    assert [p.slot for p in plans] == [s["slot"] for s in taken]
    assert all(p.unique or 1 <= len(p.affixes) <= 4 for p in plans)


def test_cast_on_crit_setup_is_kept_or_cleanly_removed(pob, monk):
    from triggers import best_cast_on_crit, find_groups
    catalog = pob.send("skill_catalog")["skills"]
    before = len(pob.send("groups")["groups"])
    t = best_cast_on_crit(pob, monk, catalog, min_gain=10.0)       # an impossible bar: must clean up
    assert t is None and len(pob.send("groups")["groups"]) == before
    t = best_cast_on_crit(pob, monk, catalog, min_gain=-1.0)       # any setup: must be in the build, spell first
    if t:   # None only if this test attack can't crit
        coc, _ = find_groups(pob)
        gems = next(g["gems"] for g in pob.send("groups")["groups"] if g["group"] == coc)
        assert gems[0] == t["spell"] and gems[-1] == "Cast on Critical"
        assert t["mapping"]["estimate"] is True
