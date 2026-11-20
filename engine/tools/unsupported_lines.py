"""Unique lines Path of Building can't read (Lodestone false-lead guard).

A line PoB doesn't support does nothing in its maths, so any scan result on that unique may be wrong: Maligaro's
Virtuosity's "Your Critical Hit Chance cannot be Rerolled" made Oracle look x2.73 (2026-11-20). This lists every
unique's unsupported lines, so scan reports can tag them and patch day can see which new lines PoB doesn't know yet.

    python tools/unsupported_lines.py run      -> data/breaker/unsupported.json + .txt
    python tools/unsupported_lines.py report
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ENGINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ENGINE))
OUT = ENGINE / "data" / "breaker" / "unsupported.json"


def collect(pob) -> dict[str, list[str]]:
    from pob import PoBError
    out: dict[str, list[str]] = {}
    for u in pob.send("list_uniques")["uniques"]:
        name = u["name"].split(",")[0]
        try:
            lines = pob.send("item_lines", raw=u["raw"])
        except PoBError:
            continue
        bad = [l for l in lines.get("unsupported") or [] if l]
        if bad:
            out.setdefault(name, [])
            out[name] += [l for l in bad if l not in out[name]]
    return out


def flagged(names, data: dict | None = None) -> set[str]:
    """The uniques among `names` with at least one line PoB can't read (for tagging scan reports)."""
    d = data if data is not None else (json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {"uniques": {}})
    return {n for n in names if n in d["uniques"]}


def report(d: dict) -> str:
    u = d["uniques"]
    rows = [f"{len(u)} uniques have lines Path of Building can't read (PoB {d.get('pob_version', '?')}). "
            "Scan results on these may be wrong; check the line before calling a lead."]
    for name in sorted(u):
        rows.append(f"  {name}")
        rows += [f"      {l}" for l in u[name]]
    return "\n".join(rows)


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"
    if cmd == "run":
        from pob import PoB
        with PoB() as p:
            p.new()
            d = {"pob_version": getattr(p, "version", None), "patch": getattr(p, "patch", None),
                 "updated": time.strftime("%Y-%m-%d %H:%M"), "uniques": collect(p)}
        OUT.write_text(json.dumps(d, indent=1, ensure_ascii=False), encoding="utf-8")
        OUT.with_suffix(".txt").write_text(report(d) + "\n", encoding="utf-8")
    d = json.loads(OUT.read_text(encoding="utf-8"))
    print(report(d))


if __name__ == "__main__":
    main()
