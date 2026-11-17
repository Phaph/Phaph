"""Fetch what the meta plays from poe.ninja (PoE 2 builds) into engine/data/meta_usage.json.

Usage:
    python engine/tools/fetch_meta.py               # newest softcore trade league
    python engine/tools/fetch_meta.py --league "Forbidden Rites"

Output: the share of ladder characters using each ascendancy, main skill, unique and keystone:
    {"league": ..., "characters": 124102, "fetched": ..., "ascendancy": {"Gemling Legionnaire": 0.32, ...},
     "skill": {...}, "unique": {...}, "keystone": {...}}
The off-meta toggle (engine/meta.py) scores builds down by how popular their parts are.

poe.ninja's builds page answers in protobuf, with names in separate "dictionary" files (a small binary
format, NDIC). Both are decoded here without extra libraries. One search request plus a few dictionaries,
an identifying User-Agent, and run it daily at most (the result is cached in the repo file).
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://poe.ninja/poe2/api"
USER_AGENT = "poe2-build-optimizer/0.1 (meta usage import, run at most daily)"
OUT = Path(__file__).resolve().parents[1] / "data" / "meta_usage.json"
# poe.ninja dimension -> our key
DIMENSIONS = {"class": "ascendancy", "skills": "skill", "items": "unique", "keypassives": "keystone"}


def _get(path: str, **params) -> bytes:
    url = f"{BASE}/{path}" + (f"?{urllib.parse.urlencode(params)}" if params else "")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def _varint(b: bytes, i: int) -> tuple[int, int]:
    r = s = 0
    while True:
        c = b[i]
        i += 1
        r |= (c & 0x7F) << s
        s += 7
        if c < 0x80:
            return r, i


def pb_fields(b: bytes) -> list[tuple[int, int | bytes]]:
    """A protobuf message as (field number, value) pairs: varints as ints, everything length-delimited as bytes."""
    i, out = 0, []
    while i < len(b):
        key, i = _varint(b, i)
        field, wire = key >> 3, key & 7
        if wire == 0:
            v, i = _varint(b, i)
        elif wire == 2:
            n, i = _varint(b, i)
            v, i = b[i:i + n], i + n
        elif wire == 1:
            v, i = b[i:i + 8], i + 8
        elif wire == 5:
            v, i = b[i:i + 4], i + 4
        else:
            raise ValueError(f"protobuf wire type {wire}")
        out.append((field, v))
    return out


def ndic(b: bytes) -> list[str]:
    """poe.ninja name dictionary: header, block table, every string's length, then the strings."""
    if b[:4] != b"NDIC":
        raise ValueError("not a poe.ninja dictionary")
    count = struct.unpack_from("<I", b, 12)[0]
    blocks = struct.unpack_from("<I", b, 28)[0]
    i, lens = 36 + 8 * blocks, []
    while len(lens) < count:
        n, i = _varint(b, i)
        lens.append(n)
    names = []
    for n in lens:
        names.append(b[i:i + n].decode("utf-8"))
        i += n
    return names


def parse_search(b: bytes, dictionary) -> dict:
    """{"characters": N, key: {name: share}} from a search response. dictionary(hash) -> list of names."""
    result = pb_fields(dict(pb_fields(b))[1])
    total = next(v for f, v in result if f == 1)
    refs = {}
    for f, v in result:
        if f == 6:
            d = dict(pb_fields(v))
            refs[d[1].decode()] = d[2].decode()
    out: dict = {"characters": total}
    for f, v in result:
        if f != 2:
            continue
        dim = pb_fields(v)
        name = dim[0][1].decode()
        if name not in DIMENSIONS:
            continue
        names = dictionary(refs[dim[1][1].decode()])
        shares = {}
        for g, entry in dim:
            if g != 3:
                continue
            e = dict(pb_fields(entry))
            key, n = e.get(1, 0), e.get(2, 0)
            if key < len(names):
                shares[names[key]] = round(n / total, 5)
        out[DIMENSIONS[name]] = dict(sorted(shares.items(), key=lambda kv: -kv[1]))
    return out


def newest_build_league() -> tuple[str, str, str]:
    """(name, snapshot version, overview) of the first softcore, non-SSF, non-Standard build league."""
    state = json.loads(_get("data/index-state"))
    for s in state["snapshotVersions"]:
        name = s["name"]
        if not name.startswith(("HC ", "SSF ")) and name != "Standard" and "SSF" not in name:
            return name, s["version"], s["snapshotName"]
    raise SystemExit("No build league found on poe.ninja")


def fetch(league: str | None = None) -> dict:
    state = json.loads(_get("data/index-state"))
    snaps = state["snapshotVersions"]
    snap = next((s for s in snaps if s["name"] == league), None) if league else None
    if snap is None:
        name, version, overview = newest_build_league()
    else:
        name, version, overview = snap["name"], snap["version"], snap["snapshotName"]
    cache: dict[str, list[str]] = {}

    def dictionary(h: str) -> list[str]:
        if h not in cache:
            cache[h] = ndic(_get(f"builds/dictionary/{h}"))
        return cache[h]

    data = parse_search(_get(f"builds/{version}/search", overview=overview), dictionary)
    return {"league": name, "fetched": datetime.now(timezone.utc).isoformat(timespec="seconds"), **data}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--league")
    args = ap.parse_args()
    data = fetch(args.league)
    if data["characters"] < 1000:
        sys.exit(f"Only {data['characters']} characters on poe.ninja: not enough to call anything meta. Kept the old file.")
    OUT.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{data['league']}: {data['characters']:,} characters")
    for key in DIMENSIONS.values():
        top = list(data.get(key, {}).items())[:5]
        print(f"  {key:<10} " + ", ".join(f"{n} {s:.0%}" for n, s in top))


if __name__ == "__main__":
    main()
