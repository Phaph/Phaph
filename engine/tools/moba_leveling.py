"""How many main skills do real guides use from Act 1 to endgame? (task 55; leveling.MAX_SKILLS = 3, "4 if guides do")

Mobalytics pages are behind Cloudflare from the server, so this reads Wayback Machine copies of mobalytics.gg/poe-2/builds/*.
Each page carries its state (window.__PRELOADED_STATE__): variants with a title ("Act 1", "Maps"...) and skill-gem slots.
A variant's main skill = the active skill with the most supports in it (a guess at "main": heralds / auras / curses
rarely carry the most supports; on a tie the first slot listed wins, so this is a rough count). Leveling variants = titles that name an act, the campaign, leveling, interludes or a level.

  python3 engine/tools/moba_leveling.py fetch [--limit 300]   -> data/moba_leveling.json (resumable; raw pages cached in ~/.cache)
  python3 engine/tools/moba_leveling.py report
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ENGINE = Path(__file__).resolve().parent.parent
OUT = ENGINE / "data" / "moba_leveling.json"
CACHE = Path.home() / ".cache" / "moba_archive"
CDX = "https://web.archive.org/cdx/search/cdx"
LEVELING = re.compile(r"\bact\s*\d|\bacts?\b|campaign|level(l)?ing|interlude|\blvl\b|\blevel\s*\d|\bstarter\b.*act", re.I)
ENDGAME = re.compile(r"map|endgame|end game|pinnacle|uber|boss|t1[0-9]|atlas|final|bis|late", re.I)


def _get(url, tries=4, timeout=200):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "guide-research"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(10 * (i + 1))


def guide_urls():
    q = urllib.parse.urlencode({"url": "mobalytics.gg/poe-2/builds/", "matchType": "prefix", "from": "2025",
                                "output": "json", "fl": "timestamp,original", "filter": "statuscode:200",
                                "limit": "50000"})
    rows = json.loads(_get(f"{CDX}?{q}"))[1:]
    latest = {}
    for ts, url in rows:
        base = url.split("?")[0].rstrip("/")
        slug = base.rsplit("/builds/", 1)[-1]
        if not slug or "/" in slug or slug == "builds":
            continue
        if ts > latest.get(slug, ("", ""))[0]:
            latest[slug] = (ts, base)
    return latest


def state(html: str):
    i = html.find("window.__PRELOADED_STATE__")
    if i < 0:
        return None
    j = html.index("=", i) + 1
    return json.JSONDecoder().raw_decode(html[j:].lstrip())[0]


def parse_guide(st):
    g = (st.get("poe2State") or {}).get("apollo", {}).get("graphql", {})
    titles = {v["id"]: v.get("title") for k, v in g.items()
              if k.startswith("NgfDocumentCmWidgetContentVariantsV1DataChildVariant") and isinstance(v, dict)}
    docs = [v["data"] for k, v in g.items() if k.startswith("Poe2UserGeneratedDocument:") and
            isinstance(v, dict) and isinstance(v.get("data"), dict) and v["data"].get("buildVariants")]
    if not docs:
        return None
    d = docs[0]
    variants = []
    for v in d["buildVariants"].get("values") or []:
        slots = ((v.get("skillGems") or {}).get("gems")) or []
        skills = []
        for s in slots:
            a = s.get("activeSkill") or {}
            if a.get("name"):
                subs = [x for x in (s.get("subSkills") or []) if x.get("gemType") == "SUPPORT"]
                skills.append((a["name"], len(subs)))
        main = max(skills, key=lambda x: x[1])[0] if skills else None
        variants.append({"title": titles.get(v.get("id")), "main": main, "skills": skills})
    return {"name": d.get("name"), "variants": variants}


def cmd_fetch(limit=300):
    CACHE.mkdir(parents=True, exist_ok=True)
    out = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {"guides": {}}
    urls = guide_urls()
    print(len(urls), "archived guide pages")
    done = 0
    for slug, (ts, base) in sorted(urls.items(), key=lambda x: x[1][0], reverse=True):
        if slug in out["guides"]:
            continue
        if done >= limit:
            break
        p = CACHE / f"{slug}_{ts}.html"
        try:
            if not p.exists():
                p.write_bytes(_get(f"https://web.archive.org/web/{ts}id_/{base}"))
            st = state(p.read_text(encoding="utf-8", errors="replace"))
            gd = parse_guide(st) if st else None
        except Exception as e:
            print(slug, "FAILED", e)
            continue
        out["guides"][slug] = {"snapshot": ts, **(gd or {"name": None, "variants": []})}
        done += 1
        if done % 10 == 0:
            OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
            print(done, slug)
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")


def mains(g):
    """(leveling mains in order, endgame main) for one guide, or None if it has no leveling variant."""
    lev = [v for v in g["variants"] if v.get("title") and LEVELING.search(v["title"]) and v.get("main")]
    end = [v for v in g["variants"] if v.get("title") and not LEVELING.search(v["title"]) and v.get("main")]
    if not lev or not end:
        return None
    from collections import Counter
    return [v["main"] for v in lev], Counter(v["main"] for v in end).most_common(1)[0][0]


def cmd_report():
    d = json.loads(OUT.read_text(encoding="utf-8"))["guides"]
    rows = []
    for slug, g in d.items():
        m = mains(g)
        if m:
            lev, end = m
            n = len(set(lev) | {end})
            rows.append((n, slug, lev, end))
    print(f"{len(d)} guides read, {len(rows)} with leveling and endgame variants")
    if not rows:
        return
    from collections import Counter
    c = Counter(r[0] for r in rows)
    for n in sorted(c):
        print(f"  {n} main skill(s) Act 1 -> endgame: {c[n]} guides ({100 * c[n] / len(rows):.0f}%)")
    print("Guides over 3:")
    for n, slug, lev, end in sorted(rows, reverse=True):
        if n > 3:
            print(f"  {n}  {slug}: {' > '.join(dict.fromkeys(lev))} => {end}")
    byend = {}
    for n, slug, lev, end in rows:
        byend.setdefault(end, []).append(n)
    print("By endgame main skill (2+ guides): skill, guides, counts")
    for k, v in sorted(byend.items(), key=lambda x: -len(x[1])):
        if len(v) >= 2:
            print(f"  {k:28s} {len(v):3d}  {sorted(v)}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    if a[0] == "fetch":
        cmd_fetch(int(a[a.index("--limit") + 1]) if "--limit" in a else 300)
    elif a[0] == "report":
        cmd_report()
    else:
        sys.exit(__doc__)
