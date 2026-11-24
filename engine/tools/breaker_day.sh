#!/bin/bash
# Breaker patch-day run: every Breaker scan in one go, on whatever game data the engine image has now.
# Use it whenever the game data changes (a PoB update, our own export after patch notes, launch day) or as a check.
#
#   ~/phaph/engine/tools/breaker_day.sh            (server; about 1 hour on 6 cores)
#   CPUS=8 SCALER=1 engine/tools/breaker_day.sh    (also re-run the scaler scan on every saved build)
#   PATCH=engine/data/patches/1_0.json engine/tools/breaker_day.sh   (patch-notes mode: scan the patched game)
#
# Writes engine/data/breaker/day/<date>/ :
#   text_new.txt     risky wording that is NEW or CHANGED since the last text scan (read this first: new content
#                    breaks first, research/broken_builds.md pattern 3)
#   text_all.txt     the top of the full text scan
#   conditions.txt   payoffs: skills whose damage jumps far more than usual under one enemy condition (combo halves;
#                    huge ones are Breaker leads)
#   scaler.json      (SCALER=1) stat elasticity per saved build
#   SUMMARY.md       the above, short, for Kyle and the morning report
# then commits and pushes them. Never touches the live site.
set -u
cd "$(dirname "$0")/../.."
export MSYS_NO_PATHCONV=1
HOST_DIR=$(pwd -W 2>/dev/null || pwd)
DAY=engine/data/breaker/day/$(date +%F)
mkdir -p "$DAY"
CPUS=${CPUS:-6}
JOBS_VOL=${JOBS_VOL:-phaph_jobs}
# PATCH=engine/data/patches/<patch>.json: every scan runs on the patched game (patch-notes mode, pob.apply_patch_file)
PATCH_ENV=()
[ -n "${PATCH:-}" ] && PATCH_ENV=(-e "PATCH_FILE=/app/engine_src/${PATCH#engine/}")
run() {   # run a command in the engine image with the repo's engine code
  docker run --rm --cpus "$CPUS" "${PATCH_ENV[@]}" -v "$HOST_DIR/engine:/app/engine_src" -v "$JOBS_VOL:/data:ro" poe2-optimizer sh -c \
    "cp /app/engine_src/*.py /app/engine_src/runner.lua /app/engine/ && cp -r /app/engine_src/tools /app/engine/ && cp /app/engine_src/data/*.json /app/engine/data/ && cd /app/engine && $1"
}
echo "$(date -u +%FT%TZ) Breaker day run -> $DAY"

# 1. Text scan, and what's new since the last one.
B=engine/data/breaker
[ -f $B/text_scan.json ] && cp $B/text_scan.json "$DAY/text_scan_before.json"
run "python text_scan.py scan --out /app/engine_src/data/breaker/text_scan.json" > "$DAY/text_all.txt" 2>&1
if [ -f "$DAY/text_scan_before.json" ]; then
  run "python text_scan.py diff /app/engine_src/${DAY#engine/}/text_scan_before.json /app/engine_src/data/breaker/text_scan.json" > "$DAY/text_new.txt" 2>&1
else
  echo "(no earlier scan to compare with)" > "$DAY/text_new.txt"
fi

# Patch-notes mode: the patched game's text stays with the day; the baseline stays the real game, for the next diff.
if [ -n "${PATCH:-}" ]; then
  cp $B/text_scan.json "$DAY/text_scan_patched.json"
  [ -f "$DAY/text_scan_before.json" ] && cp --remove-destination "$DAY/text_scan_before.json" $B/text_scan.json
fi

# 2. Condition scan, fresh.
run "python condition_scan.py run --workers $CPUS --out /app/engine_src/${DAY#engine/}/conditions.json" > "$DAY/conditions_run.log" 2>&1
run "python condition_scan.py report /app/engine_src/${DAY#engine/}/conditions.json" > "$DAY/conditions.txt" 2>&1

# 3. Scaler scan on every saved build (optional: slower).
if [ "${SCALER:-0}" = 1 ]; then
  run "python breaker.py scan --jobs /data/jobs.sqlite3 --out /app/engine_src/${DAY#engine/}/scaler.json" > "$DAY/scaler.log" 2>&1
fi

# 3b. Unique lines PoB can't read, and which are new since the last run (results on those uniques may be wrong).
[ -f $B/unsupported.json ] && cp $B/unsupported.json "$DAY/unsupported_before.json"
run "python tools/unsupported_lines.py run >/dev/null && cp data/breaker/unsupported.* /app/engine_src/data/breaker/" > /dev/null 2>&1
python3 - "$DAY/unsupported_before.json" $B/unsupported.json > "$DAY/unsupported_new.txt" <<'PY'
import json, os, sys
old = json.load(open(sys.argv[1]))["uniques"] if os.path.exists(sys.argv[1]) else {}
new = json.load(open(sys.argv[2]))["uniques"]
rows = [(n, l) for n, ls in new.items() for l in ls if l not in old.get(n, [])]
print(f"{len(rows)} unreadable unique lines new since the last run ({len(new)} uniques have some):")
for n, l in rows: print(f"  {n}: {l}")
PY
if [ -n "${PATCH:-}" ] && [ -f "$DAY/unsupported_before.json" ]; then
  cp $B/unsupported.json "$DAY/unsupported_patched.json"; git checkout -q -- $B/unsupported.json $B/unsupported.txt
fi

# 4. Summary.
{
  echo "# Breaker day run $(date +%F)"
  echo
  echo "Game data: $(head -1 "$DAY/text_all.txt")"
  echo
  echo "## New or changed risky wording (read first)"
  echo '```'; head -40 "$DAY/text_new.txt"; echo '```'
  echo
  echo "## Payoffs (skills that jump under one enemy condition)"
  echo '```'; head -25 "$DAY/conditions.txt"; echo '```'
  echo
  echo "## Unique lines PoB can't read yet (new since last run; results on these uniques may be wrong)"
  echo '```'; head -30 "$DAY/unsupported_new.txt"; echo '```'
} > "$DAY/SUMMARY.md"

git add "$DAY" $B/text_scan.json $B/unsupported.json $B/unsupported.txt 2>/dev/null
git -c user.name=Claude -c user.email=noreply@anthropic.com commit -q -m "Breaker day run $(date +%F)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- "$DAY" $B/text_scan.json $B/unsupported.json $B/unsupported.txt && git pull -q --rebase && git push -q
echo "$(date -u +%FT%TZ) Breaker day run finished: $DAY/SUMMARY.md"
