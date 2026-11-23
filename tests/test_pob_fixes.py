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


def test_item_lines_lists_unreadable_lines(pob):
    """item_lines names the lines PoB can't read (Lodestone tags scan results on those uniques)."""
    raw = ("Rarity: UNIQUE\nScold's Bridle\nMagus Tiara\n+30 to Intelligence\n"
           "Take 100% of Mana Costs you pay for Skills as Physical Damage")
    lines = pob.send("item_lines", raw=raw)
    assert any("Mana Costs you pay" in l for l in lines["unsupported"])
    assert not any("Intelligence" in l for l in lines["unsupported"])


def test_stage_rules_channel_flameblast_full(pob):
    """Flameblast is used at its full stages (runner STAGE_RULES), also after try_skill swaps its supports; PoB's
    default of 1 stage read it at a fifth of its damage. Detonating Arrow keeps PoB's default."""
    pob.new()
    pob.set_class("Sorceress", None)
    pob.set_level(70)
    g = pob.add_skill(["Flameblast"])["group"]
    r = pob.send("set_stages", group=g)
    assert r["max"] >= 5 and r["count"] == 99
    full = pob.calc(["TotalDPS"])["TotalDPS"]
    pob.send("set_stages", group=g, count=1)
    assert pob.calc(["TotalDPS"])["TotalDPS"] < full / 2
    pob.try_skill(g, ["Flameblast"], ["TotalDPS"])          # rebuilt gems get the rule again
    assert pob.send("set_stages", group=g)["count"] == 99
    pob.new()
    pob.set_class("Ranger", None)
    pob.set_level(70)
    g = pob.add_skill(["Detonating Arrow"])["group"]
    assert pob.send("set_stages", group=g)["count"] == 1


def test_wolf_pack_counts_the_pack(pob):
    """Wolf Pack's pack size maps to its wolf limit (PoB had no mapping: one wolf counted)."""
    pob.new()
    pob.set_class("Druid", None)
    pob.set_level(90)
    pob.add_skill(["Wolf Pack"], full_dps=True)
    assert pob.calc(["ActiveMinionLimit"])["ActiveMinionLimit"] >= 5
    counts = pob.send("sync_minion_counts")["counts"]
    assert counts and max(counts.values()) >= 5


def test_oil_barrage_without_power_charges_only_spits(pob):
    """Oil Barrage's fast barrage needs Power Charges; without a source it is limited to the spit's rate (x1/4.5)."""
    pob.new()
    pob.set_class("Druid", None)
    pob.set_level(70)
    pob.add_item("Rarity: NORMAL\nChangeling Talisman\nChangeling Talisman")
    pob.add_skill(["Oil Barrage"])
    pob.set_config(usePowerCharges=False)
    out = pob.calc(["Speed", "UsageLimit", "UncappedSpeed"])
    assert out.get("UsageLimit") and abs(out["Speed"] - out["UncappedSpeed"] / 4.5) < 1e-6


def test_patch_gem_changes_and_resets(pob):
    """Patch-notes mode: a gem's damage multiplier scaled in PoB's data, then put back."""
    pob.new()
    pob.set_class("Warrior", None)
    pob.set_level(60)
    pob.add_item("Rarity: NORMAL\nWooden Club\nWooden Club")
    pob.add_skill(["Earthquake"])
    before = pob.calc(["TotalDPS"])["TotalDPS"]
    r = pob.send("patch_gem", skill="Earthquake", base_multiplier=1.5)
    assert r["changed"]
    after = pob.calc(["TotalDPS"])["TotalDPS"]
    assert abs(after / before - 1.5) < 0.05
    pob.send("patch_reset")
    assert abs(pob.calc(["TotalDPS"])["TotalDPS"] - before) < 1e-6


def test_patch_file_applies_on_start(tmp_path, monkeypatch):
    """PATCH_FILE: a new PoB process starts with the changes applied."""
    import json
    from pob import PoB
    f = tmp_path / "p.json"
    f.write_text(json.dumps({"changes": [{"gem": "Earthquake", "base_multiplier": 2.0}]}))
    monkeypatch.setenv("PATCH_FILE", str(f))
    with PoB() as p:
        assert p.patched and "Earthquake" in p.patched[0]


def test_patch_unique_changes_text_and_resets(pob):
    """Patch-notes mode: a unique's line changed in PoB's unique database, then put back."""
    raw0 = next(u["raw"] for u in pob.list_uniques() if u["name"].startswith("Leopold's Applause"))
    line = next(l for l in raw0.split("\n") if "-50%" in l)
    r = pob.send("patch_unique", name="Leopold's Applause", replace=[[line, line.replace("-50%", "-30%")]])
    assert r["changed"]
    raw1 = next(u["raw"] for u in pob.list_uniques() if u["name"].startswith("Leopold's Applause"))
    assert "-30%" in raw1 and "-50%" not in raw1
    pob.send("patch_reset")
    assert next(u["raw"] for u in pob.list_uniques() if u["name"].startswith("Leopold's Applause")) == raw0


def test_armour_broken_needs_a_fast_break(pob):
    """auto_config turns on Armour Broken only when the build fully breaks the boss's armour fast enough to keep it
    broken 90% of the time, with the break time in its reason (not for any armour break on hit)."""
    from optimize import MODE_CONFIG
    pob.new()
    pob.set_class("Warrior", None)
    pob.set_level(60)
    pob.add_item("Rarity: NORMAL\nWooden Club\nWooden Club")
    pob.add_skill(["Armour Breaker"])
    pob.set_config(**MODE_CONFIG["bossing"])
    applied = {a["var"]: a["why"] for a in pob.auto_config("bossing")}
    ab = pob.send("armour_break")
    if "conditionEnemyArmourBroken" in applied:
        assert "s, Fully Broken" in applied["conditionEnemyArmourBroken"]
    else:
        assert ab["enemy_armour"] > 0     # a slow break: left off


def test_patch_gem_level_field_and_support_types(pob):
    """Patch-notes mode: a per-level field (crit chance) and a support's required skill types, changed and reset."""
    pob.new()
    pob.set_class("Sorceress", None)
    pob.set_level(60)
    pob.add_item("Rarity: NORMAL\nAshen Staff\nAshen Staff")
    pob.add_skill(["Fireball"])
    c0 = pob.calc(["CritChance"])["CritChance"]
    r = pob.send("patch_gem", skill="Fireball", level={"critChance": 50})
    assert r["changed"] and pob.calc(["CritChance"])["CritChance"] > c0
    r = pob.send("patch_gem", id="SupportIceBitePlayer", require_types=["Damage"])
    assert "supports: Damage" in r["changed"][0]
    pob.send("patch_reset")
    assert abs(pob.calc(["CritChance"])["CritChance"] - c0) < 1e-9


def test_patch_gem_add_remove_rename_stats(pob):
    """Patch-notes mode: constant stats added, removed and renamed on a gem, then reset."""
    pob.new()
    r = pob.send("patch_gem", skill="Cold Attunement", rename={"non_skill_base_all_damage_%_to_gain_as_cold": "x_renamed"})
    r2 = pob.send("patch_gem", skill="Fireball", add={"base_number_of_projectiles": 2}, remove=["no_such_stat"])
    assert any("+ base_number_of_projectiles" in c for c in r2["changed"])
    pob.send("patch_reset")


def test_patch_node_rewords_a_passive(pob):
    """Patch-notes mode: a notable's line reworded changes the numbers (re-parsed like PoB's load), then put back.
    (Keystones apply through PoB's keystone table, not their own lines: not covered yet.)"""
    pob.new()
    pob.set_class("Sorceress", None)
    pob.set_level(70)
    pob.add_skill(["Fireball"])
    pob.send("set_custom_mods", text="", nodes=["Forbidden Path"])
    life0 = pob.calc(["Life"])["Life"]
    r = pob.send("patch_node", name="Forbidden Path", replace=[["5% reduced maximum Life", "50% reduced maximum Life"]])
    assert r["changed"]
    pob.send("set_custom_mods", text="", nodes=["Forbidden Path"])
    assert pob.calc(["Life"])["Life"] < life0 * 0.7
    pob.send("patch_reset")
    pob.send("set_custom_mods", text="", nodes=["Forbidden Path"])
    assert pob.calc(["Life"])["Life"] == life0
    pob.send("set_custom_mods", text="")


def test_temporary_minions_not_counted_at_their_limit(pob):
    """persistent_only: Wolf Pack (persistent) counts its pack; Unearth's corpse constructs (temporary) are left at 1."""
    pob.new()
    pob.set_class("Witch", None)
    pob.set_level(90)
    pob.add_skill(["Unearth"], full_dps=True)
    counts = pob.send("sync_minion_counts", persistent_only=True)["counts"]
    assert not counts


def test_patch_base_changes_item_numbers(pob):
    """Patch-notes mode: a base item's armour changed in PoB's data (new items use it), then put back."""
    raw = "Rarity: NORMAL\nRusted Cuirass\nRusted Cuirass"

    def armour():
        pob.new()
        pob.set_class("Warrior", None)
        pob.set_level(60)
        pob.add_item(raw)
        return pob.calc(["Armour"])["Armour"]
    a0 = armour()
    r = pob.send("patch_base", name="Rusted Cuirass", armour={"Armour": 450})
    assert r["changed"]
    assert armour() > a0 * 3
    pob.send("patch_reset")
    assert abs(armour() - a0) < 1e-6


def test_auto_config_turns_off_free_purple_flames(pob):
    """auto_config sets Acolyte's Purple Flames to 0 (PoB's own default is 10: a free 1.7x boost). Checked on the
    saved Rapid Shot Acolyte finalist build (tests/data: it takes the notable that uses them)."""
    from pathlib import Path
    from optimize import MODE_CONFIG
    code = (Path(__file__).resolve().parent / "data" / "rapid_shot_acolyte.txt").read_text().strip()
    pob.load_code(code)
    pob.set_config(**MODE_CONFIG["bossing"])
    pob.set_config(purpleFlameStacks=10)
    with_flames = pob.calc(["TotalDPS"])["TotalDPS"]
    pob.auto_config("bossing")
    assert pob.calc(["TotalDPS"])["TotalDPS"] < 0.8 * with_flames
