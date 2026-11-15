

def test_stat_focus_scales_the_metric():
    from optimize import metric_for, score_of
    m = metric_for("bossing", "bleed", ["crit", "rarity"])
    assert m == "bleed+crit"
    low = {"BleedDPS": 1000, "CritChance": 5}
    high = {"BleedDPS": 1000, "CritChance": 60}
    assert score_of(high, m) > score_of(low, m) * 1.4
    assert score_of({"BleedDPS": 1000, "CritChance": 500}, m) == score_of({"BleedDPS": 1000, "CritChance": 100}, m)


def test_untagged_attacks_count_as_physical():
    from optimize import damage_types
    assert "Physical" in damage_types(["Attack", "CrossbowAmmoSkill"])        # crossbow ammo: bleed works
    assert "Physical" not in damage_types(["Attack", "Lightning"])
    assert "Physical" not in damage_types(["Spell"])


def test_ailment_score_demands_the_ailment():
    from optimize import score_of
    no_bleed = {"TotalDPS": 1_000_000, "BleedDPS": 0}
    real_bleed = {"TotalDPS": 20_000, "BleedDPS": 15_000}
    assert score_of(no_bleed, "bleed") == 0
    assert score_of(real_bleed, "bleed") > score_of({"TotalDPS": 200_000, "BleedDPS": 15_000}, "bleed")
