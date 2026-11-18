"""Merge A-to-Z sweep lanes (night_sweep.sh SHARD/SHARDS) into one results file and print the report.

    python engine/tools/az_merge.py engine/data/baseline/az_sweep.json engine/data/baseline/az_sweep_pc*.json
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def merge(out: Path, parts: list[Path]) -> dict:
    merged = {"results": {}, "timeouts": {}}
    for p in parts:
        d = json.loads(p.read_text(encoding="utf-8"))
        for k in ("pob_version", "updated"):
            if d.get(k):
                merged[k] = max(merged.get(k) or "", d[k])
        merged["results"].update(d.get("results") or {})
        merged["timeouts"].update(d.get("timeouts") or {})
    out.write_text(json.dumps(merged, indent=1, ensure_ascii=False), encoding="utf-8")
    return merged


if __name__ == "__main__":
    out, parts = Path(sys.argv[1]), [Path(p) for p in sys.argv[2:] if Path(p).resolve() != Path(sys.argv[1]).resolve()]
    m = merge(out, parts)
    passed = [k for k, r in m["results"].items() if not r.get("fails")]
    print(f"{len(m['results'])} builds, {len(passed)} pass every check, {len(m['timeouts'])} timed out")
    for k, r in m["results"].items():
        print(f"  {k:<32} {str(r.get('skill')):<22} {str(r.get('weapon')):<16} {r.get('total_dps', 0):>12,}  "
              f"{r.get('seconds', 0) // 60:>3} min  {'; '.join(r.get('fails') or [])[:90]}")
