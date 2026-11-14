"""Collect item and gem icon links (GGG's own image server, web.poecdn.com) into engine/data/icons.json.

Usage:
    python engine/tools/fetch_icons.py                 # newest softcore trade league, 80 characters
    python engine/tools/fetch_icons.py --characters 150

GGG's image links carry a hash, so they can't be built from a game file path; we need links GGG already
made. Two places have them:
  - poe.ninja's unique price lists: one icon per unique.
  - poe.ninja's public character pages: each item's base art (a rare shows its base) and each socketed gem.
We store links only, never the images: the website loads them straight from GGG's server, the same way
poe.ninja and other fan sites do (see research/ggg-third-party-rules.md).

Output: {"uniques": {name: url}, "bases": {base type: url}, "gems": {gem name: url}}. Entries already in the
file are kept, so repeated runs (for example after a new league) only add.
Run it rarely: once per league or patch is plenty. Requests are spaced out and identify this tool.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_prices import BASE, CATEGORIES, newest_trade_league  # noqa: E402

USER_AGENT = "poe2-build-optimizer/0.1 (icon link import, run once per league)"
OUT = Path(__file__).resolve().parents[1] / "data" / "icons.json"
ICON_HOST = "https://web.poecdn.com/"
PAUSE = 1.5


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def get_json(path: str, **params) -> dict:
    return json.loads(_get(f"{BASE}/{path}" + (f"?{urllib.parse.urlencode(params)}" if params else "")))


def _column(blob: bytes, name: str) -> list[str]:
    """poe.ninja's build list is column-oriented protobuf: a column header (`name`) followed by its values as
    repeated length-prefixed strings (field 7). Reads one column's values in order."""
    header = b"\n" + bytes([len(name)]) + name.encode() + b"\x12" + bytes([len(name)]) + name.encode()
    i = blob.find(header)
    if i < 0:
        return []
    i += len(header)
    # skip any small fields before the values (e.g. " \x01")
    while i < len(blob) and blob[i] != 0x3A:
        i += 1
    out = []
    while i < len(blob) and blob[i] == 0x3A:
        i += 1
        n, shift = 0, 0
        while True:
            b = blob[i]
            i += 1
            n |= (b & 0x7F) << shift
            shift += 7
            if not b & 0x80:
                break
        out.append(blob[i:i + n].decode("utf-8", "replace"))
        i += n
    return out


def top_characters(limit: int) -> tuple[str, str, list[tuple[str, str]]]:
    """(snapshot version, overview name, [(account, character)]) for the newest league's ladder."""
    state = get_json("data/index-state")
    league = newest_trade_league()
    snap = next(s for s in state["snapshotVersions"] if s["name"] == league)
    blob = _get(f"{BASE}/builds/{snap['version']}/search?" + urllib.parse.urlencode({"overview": snap["snapshotName"]}))
    accounts, names = _column(blob, "account"), _column(blob, "name")
    pairs = list(zip(accounts, names))
    return snap["version"], snap["snapshotName"], pairs[:limit]


def _ok(url: str | None) -> bool:
    return bool(url) and url.startswith(ICON_HOST)


def harvest_character(data: dict, icons: dict) -> None:
    for it in (data.get("items") or []) + (data.get("flasks") or []) + (data.get("jewels") or []):
        item = it.get("itemData", it)
        # Normal, magic and rare items show their base's art; uniques have their own (taken from prices).
        if item.get("frameType") in (0, 1, 2) and _ok(item.get("icon")) and item.get("baseType"):
            icons["bases"].setdefault(item["baseType"], item["icon"])
        elif item.get("frameType") == 3 and _ok(item.get("icon")) and item.get("name"):
            icons["uniques"].setdefault(item["name"], item["icon"])
    for group in data.get("skills") or []:
        for gem in group.get("allGems") or []:
            item = gem.get("itemData") or {}
            name = gem.get("name") or item.get("typeLine")
            if name and _ok(item.get("icon")):
                icons["gems"].setdefault(name, item["icon"])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--characters", type=int, default=80)
    args = ap.parse_args(argv)

    icons = {"uniques": {}, "bases": {}, "gems": {}}
    if OUT.exists():
        old = json.loads(OUT.read_text(encoding="utf-8"))
        for k in icons:
            icons[k].update(old.get(k, {}))

    league = newest_trade_league()
    for cat in CATEGORIES:
        for ln in get_json("economy/stash/current/item/overview", league=league, type=cat).get("lines", []):
            if _ok(ln.get("icon")) and not ln.get("corrupted"):
                icons["uniques"].setdefault(ln["name"], ln["icon"])
        time.sleep(PAUSE)
    print(f"uniques: {len(icons['uniques'])}", file=sys.stderr)

    version, overview, chars = top_characters(args.characters)
    print(f"{len(chars)} characters from {overview}", file=sys.stderr)
    for n, (account, name) in enumerate(chars, 1):
        time.sleep(PAUSE)
        try:
            data = get_json(f"builds/{version}/character", account=account, name=name, overview=overview, timeMachine="")
        except Exception as e:  # noqa: BLE001 - a private or renamed character just gets skipped
            print(f"  skip {name}: {e}", file=sys.stderr)
            continue
        harvest_character(data, icons)
        if n % 10 == 0:
            print(f"  {n}/{len(chars)}: {len(icons['bases'])} bases, {len(icons['gems'])} gems", file=sys.stderr)

    icons = {k: dict(sorted(v.items())) for k, v in icons.items()}
    OUT.write_text(json.dumps(icons, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(icons['uniques'])} uniques, {len(icons['bases'])} bases, {len(icons['gems'])} gems -> {OUT}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
