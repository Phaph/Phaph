#!/bin/bash
# Overnight A-to-Z sweep on the server: one build per ascendancy, every check, each build in its own container with a
# time limit, so one build that hangs (the Deadeye build on 2026-11-17) is recorded and the sweep moves on.
# Results resume: builds already in the results file are skipped, so the sweep continues where it stopped.
#   nohup engine/tools/night_sweep.sh > ~/night_sweep.log 2>&1 &
set -u
cd "$(dirname "$0")/../.."
OUT=engine/data/baseline/az_sweep.json
LIMIT=${LIMIT:-2700}            # seconds per build (45 min)
CPUS=${SWEEP_CPUS:-4}           # leave the rest for the live site
N=$(docker run --rm -v "$PWD/engine:/app/engine_src" poe2-optimizer sh -c \
    "cp /app/engine_src/*.py /app/engine/ && cp -r /app/engine_src/tools /app/engine/ && cd /app/engine && python -c 'import sys; sys.path.insert(0,\"tools\"); from az_test import sweep_prompts; print(len(sweep_prompts()))'" 2>/dev/null | tail -1)
echo "$(date -u +%FT%TZ) sweep of $N builds, ${LIMIT}s limit each"
for i in $(seq 1 "$N"); do
  docker run --rm --cpus "$CPUS" --name "night-sweep-$i" -e SWEEP=1 -e WORKERS="$CPUS" \
    -v "$PWD/engine:/app/engine_src" poe2-optimizer sh -c \
    "cp /app/engine_src/*.py /app/engine_src/runner.lua /app/engine/ && cp -r /app/engine_src/tools /app/engine/ && cp /app/engine_src/data/*.json /app/engine/data/ && cd /app/engine && timeout -s KILL $LIMIT python tools/az_test.py run --only $i --out /app/engine_src/data/baseline/az_sweep.json"
  code=$?
  if [ "$code" = 137 ]; then
    echo "#$i TIMEOUT after ${LIMIT}s"
    python3 - "$OUT" "$i" "$LIMIT" <<'EOF'
import json, sys, time
out, i, limit = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
d = json.load(open(out))
d.setdefault("timeouts", {})[str(i)] = {"limit_seconds": limit, "at": time.strftime("%Y-%m-%d %H:%M")}
json.dump(d, open(out, "w"), indent=1, ensure_ascii=False)
EOF
  fi
done
echo "$(date -u +%FT%TZ) sweep finished"
