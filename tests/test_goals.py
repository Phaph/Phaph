

def test_stat_focus_scales_the_metric():
    from optimize import metric_for, score_of
    m = metric_for("bossing", "bleed", ["crit", "rarity"])
    assert m == "bleed+crit"
    low = {"BleedDPS": 1000, "CritChance": 5}
    high = {"BleedDPS": 1000, "CritChance": 60}
    assert score_of(high, m) > score_of(low, m) * 1.4
    assert score_of({"BleedDPS": 1000, "CritChance": 500}, m) == score_of({"BleedDPS": 1000, "CritChance": 100}, m)
