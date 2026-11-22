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
