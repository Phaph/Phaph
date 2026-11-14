"""Fetch unique item prices from poe.ninja (PoE 2) into engine/data/unique_prices.json.

Usage:
    python engine/tools/fetch_prices.py               # newest softcore trade league
    python engine/tools/fetch_prices.py --league "Forbidden Rites"

Output is {unique name: price in divines}, the format gear.unique_prices() reads. The engine looks
uniques up by name only, so each name gets one price:
  - corrupted copies are skipped (they carry random implicits and aren't what PoB models),
  - listings under MIN_LISTINGS are skipped (a single 45M-divine listing is price fixing, not a price),
  - the cheapest remaining base wins, preferring plain bases over league variants
    ("Runemastered ...", "Runeforged ...") because PoB has the plain item.
A unique with no trustworthy line is left out, so the engine treats it as "price unknown"
(only suggested on the "No limit" budget).

poe.ninja publishes no API terms. We keep it light: one request per category with a pause between
them, an identifying User-Agent, and run this daily at most (prices are cached in the repo file).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://poe.ninja/poe2/api"
USER_AGENT = "poe2-build-optimizer/0.1 (unique price import, run at most daily)"
CATEGORIES = ["UniqueWeapons", "UniqueArmours", "UniqueAccessories", "UniqueFlasks",
              "UniqueJewels", "UniqueCharms"]
MIN_LISTINGS = 5
LEAGUE_VARIANT_PREFIXES = ("Runemastered ", "Runeforged ")
OUT = Path(__file__).resolve().parents[1] / "data" / "unique_prices.json"
META = OUT.with_name("unique_prices.meta.json")


def get_json(path: str, **params) -> dict:
    url = f"{BASE}/{path}" + (f"?{urllib.parse.urlencode(params)}" if params else "")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def newest_trade_league() -> str:
    """First softcore, non-SSF, non-Standard league in poe.ninja's list (newest first)."""
    state = get_json("data/index-state")
    for lg in state["economyLeagues"]:
        name = lg["name"]
        if not lg["hardcore"] and name != "Standard" and "SSF" not in name:
            return name
    raise SystemExit("No trade league found on poe.ninja")


def pick_prices(lines: list[dict], min_listings: int = MIN_LISTINGS) -> dict[str, float]:
    """One price per unique name, in divines. See the module docstring for the rules."""
    best: dict[str, tuple[bool, float]] = {}   # name -> (is_league_variant, price)
    for ln in lines:
        if ln.get("corrupted") or (ln.get("listingCount") or 0) < min_listings:
            continue
        price = ln.get("primaryValue")
        if price is None:
            continue
        variant = ln.get("baseType", "").startswith(LEAGUE_VARIANT_PREFIXES)
        key = (variant, float(price))
        if ln["name"] not in best or key < best[ln["name"]]:
            best[ln["name"]] = key
    return {name: _round(price) for name, (_, price) in sorted(best.items())}


def _round(price: float) -> float:
    if price >= 10:
        return round(price)
    if price >= 1:
        return round(price, 1)
    return round(price, 3)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--league", help="poe.ninja league name (default: newest softcore trade league)")
    ap.add_argument("--min-listings", type=int, default=MIN_LISTINGS)
    args = ap.parse_args(argv)

    league = args.league or newest_trade_league()
    lines: list[dict] = []
    for i, cat in enumerate(CATEGORIES):
        if i:
            time.sleep(2)
        data = get_json("economy/stash/current/item/overview", league=league, type=cat)
        lines += data.get("lines", [])
        print(f"{cat:<18} {len(data.get('lines', [])):>4} lines", file=sys.stderr)

    prices = pick_prices(lines, args.min_listings)
    OUT.write_text(json.dumps(prices, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    META.write_text(json.dumps({
        "source": "poe.ninja",
        "league": league,
        "fetched": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "unit": "divine",
        "min_listings": args.min_listings,
        "priced_uniques": len(prices),
        "lines_seen": len(lines),
    }, indent=1) + "\n", encoding="utf-8")
    print(f"{len(prices)} uniques priced from {league} -> {OUT}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
