"""Which item bases really exist in the current league, and their pictures. Run once per league (well under an hour).

  python engine/tools/fetch_bases.py            # resumes where it stopped; same league entries are kept

For every gear, jewellery and jewel base in Path of Building's data, one search on the official trade site counts the
league's listings. A base with no listings at all isn't one players can find (e.g. a base the game doesn't drop), so
the crafter won't use it (gear.base_usable). For bases that are listed, one listing gives GGG's own picture link for
the base, added to data/icons.json, so every base the crafter can pick has a picture.

The trade site allows about 30 searches per 5 minutes per address; this waits between requests and backs off when
told to. No personal or project details are sent.
"""
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fetch_prices import newest_trade_league  # noqa: E402

import os  # noqa: E402
DATA = Path(os.environ.get("BASES_DATA_DIR") or Path(__file__).resolve().parents[1] / "data")
OUT = DATA / "base_availability.json"
ICONS = DATA / "icons.json"
UA = "poe2-build-optimizer/0.1 (base availability check, run once per league)"
TRADE = "https://www.pathofexile.com/api/trade2"
GEAR_TYPES = {"Helmet", "Body Armour", "Gloves", "Boots", "Amulet", "Ring", "Belt", "Shield", "Focus", "Quiver", "Jewel",
              "Staff", "Wand", "Sceptre", "Bow", "Crossbow", "Spear", "Flail", "Talisman", "Claw", "Dagger",
              "One Hand Mace", "Two Hand Mace", "One Hand Sword", "Two Hand Sword", "One Hand Axe", "Two Hand Axe"}
SEARCH_GAP = 10.5   # seconds: stays under 30 searches per 300 s


def request(url: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA, "Content-Type": "application/json"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = int(e.headers.get("Retry-After") or 60) + 5
                print(f"  rate limited, waiting {wait}s", flush=True)
                time.sleep(wait)
                continue
            raise
    raise RuntimeError("gave up after repeated rate limits")


JEWELLERY = {"Amulet", "Ring", "Belt", "Jewel"}
ARMOUR = {"Helmet", "Body Armour", "Gloves", "Boots", "Shield", "Focus", "Quiver"}
BRACKETS = (82, 70, 55)   # the crafter's item levels: endgame/mid, early maps, leveling


def main():
    from pob import PoB
    with PoB() as p:
        bases = p.send("bases", max_level=100)["bases"]
    bases = [b for b in bases if b["type"] in GEAR_TYPES and not b["name"].startswith("Runeforged")
             and not set(b.get("tags") or []) & {"not_for_sale", "demigods"}]
    league = newest_trade_league()
    state = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    if state.get("league") != league:
        state = {"league": league, "bases": {}}
    icons = json.loads(ICONS.read_text(encoding="utf-8"))
    checked = 0

    def available(name: str) -> bool:
        nonlocal checked
        if name in state["bases"]:
            return state["bases"][name] > 0
        try:
            res = request(f"{TRADE}/search/poe2/{urllib.parse.quote(league)}",
                          {"query": {"type": name, "status": {"option": "any"}}})
        except urllib.error.HTTPError as e:
            if e.code != 400:
                raise
            res = {}   # the trade site doesn't know this base (not in the game yet): it can't be bought
        total = res.get("total") or 0
        state["bases"][name] = total
        if total and name not in icons["bases"] and res.get("result"):
            time.sleep(2)
            got = request(f"{TRADE}/fetch/{res['result'][0]}?query={res['id']}")
            item = (got.get("result") or [{}])[0].get("item") or {}
            if item.get("icon", "").startswith("https://web.poecdn.com/"):
                icons["bases"][name] = item["icon"]
                ICONS.write_text(json.dumps(icons, indent=1, sort_keys=True), encoding="utf-8")
        state["checked"] = time.strftime("%Y-%m-%d")
        OUT.write_text(json.dumps(state, indent=1, sort_keys=True), encoding="utf-8")
        checked += 1
        print(f"  {name}: {total} listed{'' if total else '  <- not available'}", flush=True)
        time.sleep(SEARCH_GAP)
        return total > 0

    # Only bases the crafter could pick: within each type (and armour/weapon subtype), highest level first, until
    # enough listed ones are found for every item level the crafter uses. Jewellery and jewels: all of them.
    groups: dict = {}
    for b in bases:
        groups.setdefault((b["type"], b.get("subType") or ""), []).append(b)
    for (btype, sub), items in sorted(groups.items()):
        items.sort(key=lambda b: -(b.get("level") or 0))
        need = 99 if btype in JEWELLERY else 2 if btype in ARMOUR else 6
        for bracket in BRACKETS:
            found = 0
            for b in items:
                if (b.get("level") or 0) > bracket:
                    continue
                if available(b["name"]):
                    found += 1
                if found >= need:
                    break
    missing = sorted(n for n, c in state["bases"].items() if c == 0)
    print(f"done: {checked} new checks, {len(missing)} bases with no listings: {missing}")


if __name__ == "__main__":
    main()
