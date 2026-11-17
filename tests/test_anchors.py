"""Build-around anchors, the off-meta toggle and random builds."""
import random

from anchors import find_unique, resolve, unique_slot
from gear import craft_gear, make_stage
from generate import random_unique, weapon_options
from meta import meta_factor
from optimize import optimise_supports
from prompt import parse_prompt
from tools.fetch_meta import ndic, parse_search

CATALOG = {
    "classes": [{"name": "Witch", "ascendancies": ["Infernalist", "Blood Mage", "Lich"]}],
    "skills": ["Spark", "Fireball"],
    "uniques": ["Atziri's Allure", "Kalandra's Touch"],
    "keystones": ["Chaos Inoculation", "Mind Over Matter", "Resolute Technique"],
    "supports": ["Brutality I", "Brutality II", "Bleed I", "Martial Tempo II"],
}


def parse(text):
    return parse_prompt(text, CATALOG)["request"]


def test_prompt_reads_anchors_off_meta_and_random():
    assert parse("build around atziris allure")["anchor_unique"] == "Atziri's Allure"
    r = parse("ci spark witch")
    assert r["anchor_keystone"] == "Chaos Inoculation" and "es" in r["goals"] and r["skill"] == "Spark"
    assert parse("spark built around brutality")["anchor_support"] == "Brutality II"   # top tier of a typed base
    assert parse("off meta fireball")["off_meta"] is True
    assert parse("surprise me")["random"] is True
    # Support names are everyday words: "with bleed" is the ailment, not the Bleed support.
    r = parse("bleed build with bleed")
    assert r.get("ailment") == "bleed" and "anchor_support" not in r


def test_unique_slots():
    assert unique_slot({"type": "Ring"}) == "Ring 1"
    assert unique_slot({"type": "Shield"}) == "Weapon 2"
    assert unique_slot({"type": "Bow"}) == "Weapon 1"
    assert unique_slot({"type": "Jewel"}) is None


def test_offhand_anchor_picks_weapons_that_hold_it():
    bow = {"types": ["Attack", "Projectile"], "weapons": ["Bow"]}
    assert weapon_options(bow, {"_offhand": "Quiver"}) == [("Bow", None, "Quiver")]
    assert weapon_options(bow, {"_offhand": "Shield"}) == []   # a bow can't hold a shield
    spell = {"types": ["Spell"], "weapons": []}
    assert all(off == "Focus" for _, _, off in weapon_options(spell, {"_offhand": "Focus"}))


def test_off_meta_factor_scores_popular_parts_down():
    assert meta_factor() == 1
    assert meta_factor(skill="No Such Skill") == 1
    popular = max(__import__("meta").usage().get("skill", {"x": 0}).items(), key=lambda kv: kv[1])[0]
    assert meta_factor(skill=popular) < 0.5


def test_poe_ninja_formats_decode():
    # NDIC: header (count at 12, blocks at 28), block table, lengths, strings.
    names = [b"Amazon", b"Lich"]
    head = bytearray(36)
    head[:4] = b"NDIC"
    head[12] = 2
    head[28] = 1
    blob = bytes(head) + bytes(8) + bytes([6, 4]) + b"".join(names)
    assert ndic(blob) == ["Amazon", "Lich"]

    def msg(*fields):
        out = b""
        for f, v in fields:
            if isinstance(v, int):
                out += bytes([f << 3]) + bytes([v])
            else:
                out += bytes([(f << 3) | 2, len(v)]) + v
        return out
    entry = lambda k, n: msg((1, k), (2, n))
    dim = msg((1, b"class"), (2, b"class"), (3, entry(0, 30)), (3, entry(1, 70)))
    ref = msg((1, b"class"), (2, b"h1"))
    result = msg((1, 100), (2, dim), (6, ref))
    data = parse_search(msg((1, result)), lambda h: ["Amazon", "Lich"])
    assert data["characters"] == 100 and data["ascendancy"] == {"Lich": 0.7, "Amazon": 0.3}


def test_anchor_unique_is_worn_and_keystone_held(pob):
    anchors, change, notes = resolve(pob, {"anchor_unique": "Kalandra's Touch", "anchor_keystone": "Chaos Inoculation"})
    assert anchors["unique"]["slot"] == "Ring 1" and anchors["keystone"] == "Chaos Inoculation" and notes
    pob.new()
    pob.set_class("Witch", "Infernalist")
    pob.set_level(90)
    pob.add_skill(["Spark"])
    pob.anchors = {**anchors, "main": "Spark"}
    plans = craft_gear(pob, make_stage("end"), "Wand", log=lambda *a: None)
    ring = next(p for p in plans if p.slot == "Ring 1")
    assert ring.unique and ring.unique.startswith("Kalandra's Touch")
    pob.optimise_tree(refine=True, refine_seconds=3)
    names = {k["name"] for k in pob.list_keystones()}
    assert "Chaos Inoculation" in names
    assert pob.calc(["Life"]).get("Life") == 1   # CI held through the swap phase
    pob.anchors = None


def test_anchor_support_always_kept(pob, monk):
    fits = pob.send("compatible_supports", group=monk)["supports"]
    sup = sorted(fits)[len(fits) // 2]   # any support PoB says fits, not necessarily a strong one
    pob.anchors = {"support": sup, "main": "Tempest Flurry"}
    try:
        best = optimise_supports(pob, monk, "Tempest Flurry", slots=3, top_k=4, log=lambda *a: None)[0]
        assert best.supports[0] == sup and len(best.supports) <= 3
    finally:
        pob.anchors = None


def test_random_unique_fits_the_stage(pob):
    from gear import _unique_allowed
    stage = make_stage("mid")
    for seed in range(3):
        u = random_unique(pob, random.Random(seed), stage)
        assert u is None or (not u["slot"].startswith("Weapon") and _unique_allowed(u["name"], stage))
    for seed in range(3):   # the acts: only common uniques a level 12 character can wear
        u = random_unique(pob, random.Random(seed), make_stage("act1"))
        assert u is None or ((u.get("level") or 0) <= 12 and _unique_allowed(u["name"], make_stage("act1")))
    assert find_unique(pob.list_uniques(), "no such unique") is None


def test_keystone_words():
    cat = {**CATALOG, "keystones": [*CATALOG["keystones"], "Blood Magic", "Hollow Palm Technique"]}
    assert parse_prompt("blood magic spark", cat)["request"]["anchor_keystone"] == "Blood Magic"
    assert parse_prompt("unarmed build", cat)["request"]["anchor_keystone"] == "Hollow Palm Technique"
