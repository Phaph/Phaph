"""poe.ninja ladder history from the Wayback Machine (task 54).

poe.ninja keeps no old PoE 2 build leagues (index-state's oldBuildLeagues is empty), but the Wayback Machine archived
its build-search API responses (gzipped protobuf) and the dictionaries they point to. This decodes them without a
schema into per-snapshot shares: classes (ascendancies), main skills, all skills, key passives, items.

  python3 engine/tools/ninja_archive.py list fate-of-the-vaal 20251210 20260120
  python3 engine/tools/ninja_archive.py fetch fate-of-the-vaal 20251210 20260120   # -> data/ninja_archive/<overview>/<ts>.json
  python3 engine/tools/ninja_archive.py compare data/ninja_archive/fate-of-the-vaal/A.json B.json [--dim skills] [--top 25]
  python3 engine/tools/ninja_archive.py track fate-of-the-vaal "Walking Calamity" [--dim skills]

Only unfiltered overviews are fetched (no class / skill filter): shares are of every character poe.ninja indexed at
that moment. Raw downloads are cached in ~/.cache/ninja_archive (not in git).
"""
import gzip
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ENGINE = Path(__file__).resolve().parent.parent
OUT = ENGINE / "data" / "ninja_archive"
CACHE = Path.home() / ".cache" / "ninja_archive"
CDX = "https://web.archive.org/cdx/search/cdx"
DIMS = ("class", "skills", "allskills", "keypassives", "items", "weaponmode", "anointed")


def _get(url, tries=4, timeout=200):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ladder-history-research"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(5 * (i + 1))


def _cached(name, url):
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / name
    if p.exists() and p.stat().st_size:
        return p.read_bytes()
    b = _get(url)
    p.write_bytes(b)
    return b


# --- schema-less protobuf -------------------------------------------------------------------------------------------
def _varint(b, i):
    r = s = 0
    while True:
        c = b[i]
        i += 1
        r |= (c & 0x7F) << s
        s += 7
        if c < 0x80:
            return r, i


def parse(b):
    """[(field, wiretype, value)]; length-delimited values stay bytes."""
    i, out = 0, []
    while i < len(b):
        k, i = _varint(b, i)
        f, w = k >> 3, k & 7
        if w == 0:
            v, i = _varint(b, i)
        elif w == 2:
            n, i = _varint(b, i)
            v, i = b[i:i + n], i + n
        elif w == 5:
            v, i = b[i:i + 4], i + 4
        elif w == 1:
            v, i = b[i:i + 8], i + 8
        else:
            raise ValueError(f"wire type {w}")
        out.append((f, w, v))
    return out


def _ungzip(b):
    return gzip.decompress(b) if b[:2] == b"\x1f\x8b" else b


def decode_dictionary(b):
    """Dictionary file: field 1 = type ('gem', 'class'...), field 2 repeated = names (index = position)."""
    fs = parse(_ungzip(b))
    kind = next(v.decode() for f, w, v in fs if f == 1)
    return kind, [v.decode() for f, w, v in fs if f == 2]


def decode_search(b):
    """Search response -> total, {dim_id: (dict_type, {index: count})}, {dict_type: hash}."""
    top = parse(_ungzip(b))
    body = next(v for f, w, v in top if f == 1)
    total, dims, refs = None, {}, {}
    for f, w, v in parse(body):
        if f == 1 and w == 0:
            total = v
        elif f == 2:
            fs = parse(v)
            dim_id = next(x.decode() for g, _, x in fs if g == 1)
            kind = next(x.decode() for g, _, x in fs if g == 2)
            counts = {}
            for g, _, x in fs:
                if g == 3:
                    e = {h: y for h, _, y in parse(x)}
                    counts[e.get(1, 0)] = e.get(2, 0)
            dims[dim_id] = (kind, counts)
        elif f == 6:
            e = {g: x.decode() for g, _, x in parse(v)}
            refs[e[1]] = e[2]
    return total, dims, refs


# --- archive access -------------------------------------------------------------------------------------------------
def snapshots(overview, start, end):
    """Unfiltered search responses for one league overview: [(timestamp, url)], oldest first."""
    q = urllib.parse.urlencode({"url": "poe.ninja/poe2/api/builds/", "matchType": "prefix", "from": start, "to": end,
                                "output": "json", "fl": "timestamp,original", "filter": "statuscode:200",
                                "limit": "20000"})
    rows = json.loads(_get(f"{CDX}?{q}") or b"[]")[1:]
    out = {}
    for ts, url in rows:
        if "/search?" not in url:
            continue
        params = urllib.parse.parse_qs(url.split("?", 1)[1])
        if set(params) - {"overview"} or params.get("overview") != [overview]:
            continue  # filtered views (class, skill, time machine) are not the whole ladder
        out.setdefault(ts, url)
    return sorted(out.items())


def _dict_ts(h):
    q = urllib.parse.urlencode({"url": f"poe.ninja/poe2/api/builds/dictionary/{h}", "output": "json",
                                "fl": "timestamp", "filter": "statuscode:200", "limit": "1"})
    rows = json.loads(_get(f"{CDX}?{q}") or b"[]")[1:]
    return rows[0][0] if rows else None


def load_snapshot(ts, url):
    raw = _cached(f"search_{ts}.pb", f"https://web.archive.org/web/{ts}id_/{url}")
    total, dims, refs = decode_search(raw)
    names, missing = {}, []
    for kind, h in refs.items():
        p = CACHE / f"dict_{h}.pb"
        if not (p.exists() and p.stat().st_size):
            dts = _dict_ts(h)
            if not dts:
                missing.append(kind)
                continue
            _cached(p.name, f"https://web.archive.org/web/{dts}id_/https://poe.ninja/poe2/api/builds/dictionary/{h}")
        k, lst = decode_dictionary(p.read_bytes())
        names[k] = lst
    shares = {}
    for dim_id, (kind, counts) in dims.items():
        if dim_id not in DIMS or kind not in names:
            continue
        lst = names[kind]
        shares[dim_id] = {lst[i]: round(100.0 * c / total, 3) for i, c in sorted(counts.items(), key=lambda x: -x[1])
                          if i < len(lst)}
    return {"timestamp": ts, "url": url, "characters": total, "missing_dictionaries": missing,
            "note": "percent of all characters poe.ninja indexed at that moment (unfiltered overview)",
            "shares": shares}


# --- commands -------------------------------------------------------------------------------------------------------
def cmd_list(overview, start, end):
    for ts, url in snapshots(overview, start, end):
        print(ts, url)


def cmd_fetch(overview, start, end):
    d = OUT / overview
    d.mkdir(parents=True, exist_ok=True)
    for ts, url in snapshots(overview, start, end):
        p = d / f"{ts}.json"
        if p.exists():
            continue
        try:
            snap = load_snapshot(ts, url)
        except Exception as e:  # archive hiccups: report and go on
            print(ts, "FAILED", e)
            continue
        p.write_text(json.dumps(snap, indent=1, ensure_ascii=False), encoding="utf-8")
        top = list(snap["shares"].get("skills", {}).items())[:3]
        print(ts, snap["characters"], "chars; missing", snap["missing_dictionaries"] or "none", "; top", top)


def cmd_compare(a, b, dim="skills", top=25):
    A, B = (json.loads(Path(x).read_text(encoding="utf-8")) for x in (a, b))
    sa, sb = A["shares"].get(dim, {}), B["shares"].get(dim, {})
    print(f"{dim}: {A['timestamp']} ({A['characters']} chars) -> {B['timestamp']} ({B['characters']} chars), % of ladder")
    rows = sorted(set(sa) | set(sb), key=lambda k: -(abs(sb.get(k, 0) - sa.get(k, 0))))
    for k in rows[:top]:
        x, y = sa.get(k, 0), sb.get(k, 0)
        ratio = f"x{y / x:.2f}" if x else "new"
        print(f"  {k:40s} {x:7.2f} -> {y:7.2f}  ({y - x:+.2f} pts, {ratio})")


def cmd_track(overview, name, dim="skills"):
    for p in sorted((OUT / overview).glob("*.json")):
        s = json.loads(p.read_text(encoding="utf-8"))
        print(s["timestamp"], f"{s['shares'].get(dim, {}).get(name, 0):6.2f}%", f"of {s['characters']}")


def _opt(args, name, default):
    if name in args:
        i = args.index(name)
        v = args[i + 1]
        del args[i:i + 2]
        return type(default)(v)
    return default


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    cmd = args.pop(0)
    dim = _opt(args, "--dim", "skills")
    top = _opt(args, "--top", 25)
    if cmd == "list":
        cmd_list(*args)
    elif cmd == "fetch":
        cmd_fetch(*args)
    elif cmd == "compare":
        cmd_compare(*args, dim=dim, top=top)
    elif cmd == "track":
        cmd_track(*args, dim=dim)
    else:
        sys.exit(__doc__)
