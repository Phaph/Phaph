"""Fixes runner.lua makes to Path of Building's own calculations (lines PoB doesn't support)."""


def test_maligaros_stops_inevitable_crits(pob):
    """Maligaro's Virtuosity: "Your Critical Hit Chance cannot be Rerolled" turns off Inevitable Critical Hits (the
    Oracle's Forced Outcome); PoB ignored the line and gave 100% crit with a 250% bonus (Fireball Oracle x2.73)."""
    pob.new()
    pob.set_class("Druid", "Oracle")
    pob.set_level(90)
    pob.add_skill(["Fireball"])
    pob.send("set_custom_mods", text="Inevitable Critical Hits")
    assert pob.calc(["CritChance"])["CritChance"] == 100
    pob.send("set_custom_mods", text="Inevitable Critical Hits\nYour Critical Hit Chance cannot be Rerolled")
    assert pob.calc(["CritChance"])["CritChance"] < 50
    pob.send("set_custom_mods", text="")
