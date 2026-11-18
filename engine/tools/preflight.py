"""Game-data preflight: does every name and stat our code relies on still exist in the installed Path of Building?

    python tools/preflight.py          # exit code 1 if anything the engine needs is missing

Run it after every PoB update (above all PoB 1.0, see LAUNCH_1.0.md). Most game data comes from PoB, but a few
names are written in our code: ailment support tiers ("Bleed I-V"), skill tags behind prompt words, weapon types,
jewel bases, the Cast on Critical gem, aliases, output stats. If 1.0 renames one, that feature quietly stops
working; this lists them instead.

  ERROR  the engine uses it and PoB no longer has it: fix before going live
  WARN   a data file names things PoB doesn't have (prices, pictures, trade check): refresh the file
"""
import json
import re
import sys
from pathlib import Path

ENGINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ENGINE))

import gear  # noqa: E402
import generate  # noqa: E402
import goals  # noqa: E402
import guide  # noqa: E402
import jewels  # noqa: E402
import optimize  # noqa: E402
import prompt  # noqa: E402
import triggers  # noqa: E402
from pob import POB_SRC, PoB  # noqa: E402

DATA = ENGINE / "data"


def load_game(p: PoB) -> dict:
    catalog = p.send("skill_catalog")["skills"]
    return {
        "skills": {s["name"]: s for s in catalog},
        "skill_types": {t for s in catalog for t in s["types"]},
        "supports": {g["name"] for g in p.list_gems("support")},
        "gems": {g["name"] for g in p.list_gems()},
        "classes": {c["name"]: set(c["ascendancies"]) for c in p.list_classes()},
        "bases": {b["name"]: b for b in p.send("bases")["bases"]},
        "uniques": {u["name"].split(",")[0] for u in p.list_uniques()},   # PoB names are "Name, Base"
    }


def output_fields() -> list[str]:
    """Every PoB output stat our code asks for."""
    runner = (ENGINE / "runner.lua").read_text(encoding="utf-8")
    block = re.search(r"local DEFAULT_FIELDS = \{(.*?)\n\}", runner, re.S)
    lua = re.findall(r'"(\w+)"', block.group(1)) if block else []
    return sorted({*lua, *optimize.DPS_FIELDS, *optimize.CLEAR_FIELDS, *goals.FOCUS_FIELDS, *goals.GOAL_FIELDS,
                   *gear.SCORE_FIELDS, *generate.FIELDS, *triggers.ATTACK_FIELDS, *triggers.SPELL_FIELDS,
                   *guide.STAT_FIELDS, *guide.SPLIT_FIELDS})


def check(game: dict) -> tuple[list[str], list[str]]:
    errors, warns = [], []

    def need(what: str, names, have) -> None:
        missing = sorted(n for n in set(names) if n not in have)
        if missing:
            errors.append(f"{what}: {', '.join(missing)}")

    # Skill tags behind prompt words, helper kinds, ailment and damage rules.
    need("skill tags (generate.KIND_TYPES)", generate.KIND_TYPES.values(), game["skill_types"])
    need("skill tags (generate.HELPER_TYPES)", generate.HELPER_TYPES.values(), game["skill_types"])
    need("skill tags (generate.NOT_MAIN)", generate.NOT_MAIN, game["skill_types"])
    need("skill tags (triggers.NOT_TRIGGERABLE)", triggers.NOT_TRIGGERABLE, game["skill_types"])
    need("damage tags (generate.AILMENT_DAMAGE)", {t for v in generate.AILMENT_DAMAGE.values() for t in v},
         game["skill_types"])
    need("damage tags (optimize.ELEMENT_TYPES)", optimize.ELEMENT_TYPES, game["skill_types"])
    need("skill tags (Attack, Spell, Minion)", {"Attack", "Spell", "Minion"}, game["skill_types"])

    # Ailment supports that seed_ailment puts on an ailment build.
    for ailment in optimize.AILMENT_FIELD:
        pattern = re.compile(rf"{ailment.capitalize()} (I|II|III|IV|V)")
        if not any(pattern.fullmatch(s) for s in game["supports"]):
            errors.append(f'ailment supports: no "{ailment.capitalize()} I-V" support (optimize.seed_ailment)')

    # Weapon and item types.
    base_types = {b["type"] for b in game["bases"].values()}
    pairs = [*generate.SPELL_WEAPONS, *generate.MINION_WEAPONS, *generate.SHIELD_WEAPONS]
    need("weapon types (generate.*_WEAPONS)", {w for w, _, _ in pairs}, base_types)
    need("off-hand types (generate.*_WEAPONS)", {o for _, _, o in pairs if o}, base_types)
    need("weapon types (prompt.WEAPONS)", {w for ws in prompt.WEAPONS.values() for w in ws}, base_types)
    need("slot types (gear.SLOT_TYPES)", gear.SLOT_TYPES.values(), base_types)
    need("jewel bases (jewels.JEWEL_BASES)", jewels.JEWEL_BASES, game["bases"])

    # Classes and named skills.
    need("classes (generate.DEFAULT_CLASS)", generate.DEFAULT_CLASS.values(), game["classes"])
    need("skill aliases (prompt.SKILL_ALIASES)", prompt.SKILL_ALIASES.values(), game["skills"])
    rules = json.loads((DATA / "trigger_rules.json").read_text(encoding="utf-8"))
    need("trigger gem (data/trigger_rules.json)", [rules["cast_on_crit"]["gem"]], game["skills"])
    specs = []
    try:
        sys.path.insert(0, str(ENGINE / "tools"))
        from item_audit import SPECS
        specs += SPECS
    except Exception:  # noqa: BLE001
        pass
    for s in specs:
        cls, asc = s.get("class"), s.get("ascendancy")
        if cls and cls not in game["classes"]:
            errors.append(f"test build class: {cls}")
        elif asc and asc not in game["classes"].get(cls, set()):
            errors.append(f"test build ascendancy: {cls} / {asc}")
        for sk in [s.get("skill"), *(s.get("with_skills") or [])]:
            if sk and sk not in game["skills"]:
                errors.append(f"test build skill: {sk}")

    # Output stats: each must still appear in PoB's calculation code.
    src = "\n".join(f.read_text(encoding="utf-8", errors="ignore") for f in (POB_SRC / "Modules").glob("Calc*.lua"))
    dynamic = {"WithBleedDPS", "WithPoisonDPS", "WithIgniteDPS",   # built as "With"..ailment.."DPS"
               "UsageLimit", "UncappedSpeed"}   # our own (runner.lua USAGE_LIMITS), not PoB's
    for f in output_fields():
        # Minion stats are PoB's output.Minion.<stat> (runner.lua exposes MinionDPS as Minion.TotalDPS).
        bare = {"MinionDPS": "TotalDPS", "MinionDotDPS": "TotalDotDPS"}.get(f, f.removeprefix("Minion"))
        if f in dynamic or bare.endswith("HitAverage") or bare.endswith("Dot"):
            continue   # assembled from parts in PoB's code, so not greppable
        if not re.search(rf"\b{re.escape(bare)}\b", src):
            errors.append(f"output stat not in PoB's calc code: {f}")

    # Data files that name game things (refreshed per league, see LAUNCH_1.0.md).
    def stale(what: str, names, have, fix: str) -> None:
        missing = sorted(n for n in names if n not in have)
        if missing:
            sample = ", ".join(missing[:8]) + (" ..." if len(missing) > 8 else "")
            warns.append(f"{what}: {len(missing)} names PoB doesn't have ({sample}). {fix}")

    prices = json.loads((DATA / "unique_prices.json").read_text(encoding="utf-8"))
    stale("unique prices", prices, game["uniques"], "Run tools/fetch_prices.py.")
    icons = json.loads((DATA / "icons.json").read_text(encoding="utf-8"))
    stale("base pictures", icons.get("bases", {}), game["bases"], "Run tools/fetch_bases.py.")
    stale("gem pictures", icons.get("gems", {}), game["gems"], "Run tools/fetch_icons.py.")
    stale("unique pictures", icons.get("uniques", {}), game["uniques"], "Run tools/fetch_icons.py.")
    avail = json.loads((DATA / "base_availability.json").read_text(encoding="utf-8"))
    stale("trade check", avail.get("bases", {}), game["bases"], "Run tools/fetch_bases.py.")
    meta = json.loads((DATA / "unique_prices.meta.json").read_text(encoding="utf-8"))
    print(f"data files: trade check {avail.get('league')} {avail.get('checked')}, "
          f"prices {meta.get('league')} {meta.get('fetched')} (refresh both for a new league)")
    return errors, warns


def main() -> int:
    with PoB() as p:
        game = load_game(p)
    print(f"PoB {p.version}: {len(game['skills'])} skills, {len(game['supports'])} supports, "
          f"{len(game['bases'])} bases, {len(game['uniques'])} uniques, {len(game['classes'])} classes")
    errors, warns = check(game)
    for e in errors:
        print("ERROR", e)
    for w in warns:
        print("WARN ", w)
    print("preflight:", "FAIL" if errors else "ok", f"({len(errors)} errors, {len(warns)} warnings)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
