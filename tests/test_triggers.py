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
    cat = [{"name": "Comet", "types": ["Spell", "Area", "Triggerable"], "weapons": []},   # as in PoB's data
           {"name": "Herald of Ice", "types": ["Spell", "Herald", "Persistent"], "weapons": []},
           {"name": "Raise Zombie", "types": ["Spell", "Minion"], "weapons": []},
           {"name": "Wand Spell", "types": ["Spell"], "weapons": ["Wand"]},
           {"name": "Tempest Flurry", "types": ["Attack"], "weapons": ["Staff"]}]
    assert spell_candidates(cat) == ["Comet"]


def test_impossible_numbers_never_score():
    from optimize import broken_numbers, impossible, score_of, total_dps
    assert impossible(2147483647) and impossible(float("inf")) and impossible(float("nan")) and impossible(None)
    assert not impossible(36_000_000)
    assert total_dps({"FullDPS": 2147483647}) == 0
    assert score_of({"TotalDPS": float("inf")}, "total") == 0
    assert broken_numbers({"TotalDPS": 2147483647, "Life": 5000, "FullDPS": 1e6}) == ["TotalDPS"]


class AilmentPoB(FakePoB):
    """Same attack, now shocking on 25% of hits and igniting on 10%, with Comet in Cast on Elemental Ailment."""
    def send(self, cmd, **k):
        if cmd == "groups":
            return {"groups": [{"group": 1, "gems": ["Tempest Flurry"], "main": True},
                               {"group": 2, "gems": ["Cast on Elemental Ailment", "Comet"], "main": False}]}
        if cmd == "gem_info":
            out = super().send(cmd, **k)
            out["gems"]["Cast on Elemental Ailment"] = {"cast_time": 0, "cooldown": None, "types": ["Meta"], "support": False}
            return out
        return super().send(cmd, **k)

    def calc(self, fields):
        out = super().calc(fields)
        if self.main[0] == 1:
            out.update({"ShockChance": 25, "IgniteChance": 10})
        return out


def test_cast_on_elemental_ailment_energy_from_shocks_and_ignites():
    e = cast_on_crit(AilmentPoB(), 1, 2, mode="bossing", gem_level=20, rules=load_rules(), gem="Cast on Elemental Ailment")
    # 4 hits/s: 1 shock + 0.4 ignites per second, 1 energy each per monster power, boss power 20, +57% at level 20
    per_sec = (1.0 + 0.4) * 1 * 20 * 1.57
    assert e["gem"] == "Cast on Elemental Ailment"
    assert e["attack"]["crits_per_sec"] == pytest.approx(1.4)          # ailments applied per second
    assert e["casts_per_sec"] == pytest.approx(per_sec / 100)           # Comet needs 100 energy
    assert e["trigger_dps"] == pytest.approx(e["casts_per_sec"] * 800)


def test_trigger_spell_candidates():
    from triggers import spell_candidates
    cat = [{"name": "Comet", "types": ["Spell", "Damage", "Totemable", "Trappable", "Triggerable"], "weapons": []},
           {"name": "Lightning Warp", "types": ["Spell", "Movement", "Travel", "Triggerable"], "weapons": []},
           {"name": "Archmage", "types": ["Spell", "Buff", "Persistent"], "weapons": []},
           {"name": "Untriggerable Nova", "types": ["Spell", "Damage"], "weapons": []}]
    # "Totemable" is no bar (it once excluded almost every spell); teleports and buffs are; Triggerable is required.
    assert spell_candidates(cat) == ["Comet"]


def test_hit_metas_gain_energy_on_every_hit(pob):
    """Thundergod's Wrath (Mjölner) gains energy on every melee hit, not only crits, and triggers Lightning spells
    only (a Fire spell in it is ignored)."""
    from triggers import cast_on_crit
    from optimize import MODE_CONFIG
    pob.new()
    pob.set_class("Warrior", None)
    pob.set_level(60)
    pob.add_item("Rarity: NORMAL\nWooden Club\nWooden Club")
    a = pob.add_skill(["Boneshatter"])["group"]
    t = pob.add_skill(["Thundergod's Wrath", "Arc", "Fireball"], main=False)["group"]
    pob.send("set_main", group=a)
    pob.set_config(**MODE_CONFIG["mapping"])
    r = cast_on_crit(pob, a, t, mode="mapping", gem="Thundergod's Wrath")
    assert abs(r["attack"]["crits_per_sec"] - r["attack"]["hits_per_sec"]) < 1e-9     # every hit counts
    assert [s["spell"] for s in r["spells"]] == ["Arc"]
    assert r["energy"]["per_crit"] == 3.0                                             # 3 per power, normal monster
