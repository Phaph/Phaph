"""Usage limits PoB doesn't model (runner.lua USAGE_LIMITS): Hexblast only goes off on a half-expired curse."""


def test_hexblast_is_held_to_its_curse_cycle(pob):
    pob.new()
    pob.set_class("Witch", "Lich")
    pob.set_level(90)
    pob.add_skill(["Hexblast"])
    out = pob.calc(["TotalDPS", "Speed", "UsageLimit", "UncappedSpeed"])
    assert out["UsageLimit"] < 0.2 and out["Speed"] <= out["UsageLimit"] + 1e-9
    assert out["UncappedSpeed"] > out["Speed"]
    again = pob.calc(["Speed"])   # a second calc doesn't cap twice
    assert abs(again["Speed"] - out["Speed"]) < 1e-9


def test_other_skills_are_untouched(pob):
    pob.new()
    pob.set_class("Witch", "Lich")
    pob.set_level(90)
    pob.add_skill(["Spark"])
    out = pob.calc(["Speed", "UsageLimit"])
    assert "UsageLimit" not in out and out["Speed"] > 0


def test_detonate_dead_needs_corpses_against_bosses(pob):
    pob.new()
    pob.set_class("Witch", "Lich")
    pob.set_level(90)
    pob.add_skill(["Detonate Dead"])
    pob.set_config(enemyIsBoss="Pinnacle")
    boss = pob.calc(["TotalDPS", "Speed", "UsageLimit"])
    assert boss["UsageLimit"] == 0.25 and boss["Speed"] <= 0.25 + 1e-9
    pob.set_config(enemyIsBoss="None")   # maps: corpses everywhere
    maps = pob.calc(["TotalDPS", "Speed", "UsageLimit"])
    assert "UsageLimit" not in maps and maps["Speed"] > 0.25


def test_ember_fusillade_waits_for_its_volley(pob):
    pob.new()
    pob.set_class("Sorceress", "Stormweaver")
    pob.set_level(90)
    pob.add_skill(["Ember Fusillade"])
    out = pob.calc(["Speed", "UsageLimit", "UncappedSpeed", "Duration"])
    assert out["UncappedSpeed"] > out["Speed"] and out["Speed"] <= out["UsageLimit"] + 1e-9
    assert abs(out["UsageLimit"] - 10 / (10 / out["UncappedSpeed"] + out["Duration"])) < 1e-6


BOW = """Rarity: Normal
Recurve Bow
--------
Requires: Level 1"""


def test_rain_of_arrows_hits_one_target_with_only_some_arrows(pob):
    pob.new()
    pob.set_class("Ranger", "Deadeye")
    pob.set_level(90)
    pob.add_item(BOW)
    pob.add_skill(["Rain of Arrows"])
    pob.set_config(enemyIsBoss="Pinnacle")
    fields = ["TotalDPS", "HitSpeed", "Speed", "ProjectileCount", "AreaOfEffectRadius", "AreaOfEffectRadiusSecondary",
              "UsageLimit", "UncappedSpeed"]
    boss = pob.calc(fields)
    assert boss["UncappedSpeed"] > boss["HitSpeed"] and boss["UsageLimit"] == boss["HitSpeed"]   # HitSpeed basis
    R, r = boss["AreaOfEffectRadius"] / 10, boss.get("AreaOfEffectRadiusSecondary", 7) / 10
    arrows = min(boss["ProjectileCount"] * boss["Speed"], 12.5)
    assert abs(boss["HitSpeed"] - min(arrows * ((1.5 + r) / R) ** 2, 1 / 0.12)) < 1e-6
    pob.set_config(enemyIsBoss="None")   # a smaller target: fewer arrows on it
    maps = pob.calc(fields)
    assert maps["HitSpeed"] < boss["HitSpeed"]


def test_bonestorm_release_time(pob):
    """Bonestorm: each 20-spike volley also pays its release (6 cast times), not only the channel ticks."""
    pob.new()
    pob.set_class("Witch", None)
    pob.set_level(80)
    pob.add_item("Rarity: NORMAL\nAshen Staff\nAshen Staff")
    g = pob.add_skill(["Bonestorm"])["group"]
    pob.send("set_custom_mods", text="Skills fire 4 additional Projectiles")
    pob.send("set_stages", group=g, count=20)
    out = pob.calc(["HitSpeed", "UsageLimit", "UncappedSpeed", "Speed"])
    assert out.get("UsageLimit") and abs(out["HitSpeed"] - 1 / (1 / out["UncappedSpeed"] + 6 / out["Speed"])) < 1e-6
    assert out["HitSpeed"] < 0.5 * out["UncappedSpeed"]
    pob.send("set_custom_mods", text="")
