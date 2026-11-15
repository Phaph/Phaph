"""Cast on Critical energy maths (engine/triggers.py), with a fake PoB so it runs in milliseconds."""
import pytest

from triggers import cast_on_crit, find_groups, load_rules, verified


class FakePoB:
    def __init__(self):
        self.main = (1, None)

    def send(self, cmd, **k):
        if cmd == "groups":
            return {"groups": [{"group": 1, "gems": ["Tempest Flurry"], "main": True},
                               {"group": 2, "gems": ["Cast on Critical", "Comet", "Spell Echo"], "main": False}]}
        if cmd == "gem_info":
            return {"gems": {"Cast on Critical": {"cast_time": 0, "cooldown": None, "types": ["Meta"], "support": False},
                             "Comet": {"cast_time": 1.0, "cooldown": None, "types": ["Spell"], "support": False},
                             "Spell Echo": {"cast_time": 0, "cooldown": None, "types": ["Spell"], "support": True}}}
        if cmd == "set_main":
            self.main = (k["group"], k.get("skill"))
            return {}
        raise AssertionError(cmd)

    def calc(self, fields):
        if self.main[0] == 1:   # the attack: 4 hits/s, 50% crit, crits for 2x
            return {"Speed": 4, "HitChance": 100, "CritChance": 50, "CritMultiplier": 2, "AverageDamage": 1500,
                    "EnemyAilmentThreshold": 4000, "TotalDPS": 6000}
        assert self.main == (2, 2), "Comet is the 2nd active skill: the support is skipped"
        return {"TotalDPS": 500, "Speed": 0.5, "AverageDamage": 1000}


def test_energy_maths_bossing():
    rules = load_rules()
    e = cast_on_crit(FakePoB(), 1, 2, mode="bossing", gem_level=20, rules=rules)
    # 4 hits x 50% = 2 crits/s; crit 2000 vs threshold 4000 -> ratio 0.5
    assert e["attack"]["crits_per_sec"] == pytest.approx(2)
    assert e["attack"]["crit_hit"] == pytest.approx(2000)
    assert e["energy"]["threshold_ratio"] == pytest.approx(0.5)
    # 20 power x 1.57 x 0.5 = 15.7 energy per crit; Comet needs 100
    assert e["energy"]["per_crit"] == pytest.approx(15.7)
    assert e["energy"]["to_fire"] == pytest.approx(100)
    assert e["casts_per_sec"] == pytest.approx(2 * 15.7 / 100)
    comet = e["spells"][0]
    assert comet["spell"] == "Comet" and comet["damage_per_cast"] == pytest.approx(800)   # 1000 x 20% less
    assert e["trigger_dps"] == pytest.approx(e["casts_per_sec"] * 800)
    assert e["total_dps"] == pytest.approx(6000 + e["trigger_dps"])
    assert e["estimate"] is True


def test_cooldown_caps_casts_and_mapping_uses_normal_monsters():
    rules = load_rules()
    rules["monster_power"]["unique_boss"] = 2000   # absurd energy: the cooldown must cap it
    pob = FakePoB()
    orig = pob.send

    def send(cmd, **k):
        out = orig(cmd, **k)
        if cmd == "gem_info":
            out["gems"]["Comet"]["cooldown"] = 2.0
        return out
    pob.send = send
    e = cast_on_crit(pob, 1, 2, mode="bossing", rules=rules)
    assert e["spells"][0]["casts_per_sec"] == pytest.approx(0.5)
    m = cast_on_crit(FakePoB(), 1, 2, mode="mapping", rules=load_rules())
    assert m["energy"]["monster_power"] == 1 and m["energy"]["enemy_threshold"] is None


def test_unverified_rules_are_flagged_and_groups_are_found():
    assert verified() is False   # until an in-game check flips the flags
    assert find_groups(FakePoB()) == (2, [1])


def test_spell_candidates_are_plain_damaging_spells():
    from triggers import spell_candidates
    cat = [{"name": "Comet", "types": ["Spell", "Area"], "weapons": []},
           {"name": "Herald of Ice", "types": ["Spell", "Herald", "Persistent"], "weapons": []},
           {"name": "Raise Zombie", "types": ["Spell", "Minion"], "weapons": []},
           {"name": "Wand Spell", "types": ["Spell"], "weapons": ["Wand"]},
           {"name": "Tempest Flurry", "types": ["Attack"], "weapons": ["Staff"]}]
    assert spell_candidates(cat) == ["Comet"]
