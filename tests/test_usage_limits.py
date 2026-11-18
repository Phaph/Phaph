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
