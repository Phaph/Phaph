#!/bin/bash
# A-to-Z sweep: one build per ascendancy, every check, each build in its own container with a time limit, so one build
# that hangs (the Deadeye build on 2026-11-17) is recorded and the sweep moves on. Results resume: builds already in the
# results file are skipped. Runs on the server (overnight) or on Kyle's PC (faster cores, Git Bash + Docker Desktop).
#
#   server:  nohup engine/tools/night_sweep.sh > ~/night_sweep.log 2>&1 &
#   PC, 3 lanes in parallel (each its own results file; merge with az_merge.py after):
#            SHARD=0 SHARDS=3 SWEEP_CPUS=6 OUT_NAME=az_sweep_pc0.json engine/tools/night_sweep.sh
#
# Never start the app or tunnel containers on the PC: the server serves the live site.
set -u
export MSYS_NO_PATHCONV=1                       # Git Bash on Windows: keep /app paths as they are
cd "$(dirname "$0")/../.."
HOST_DIR=$(pwd -W 2>/dev/null || pwd)           # a Windows path for Docker Desktop, a normal one on Linux
OUT_NAME=${OUT_NAME:-az_sweep.json}
OUT=engine/data/baseline/$OUT_NAME
LIMIT=${LIMIT:-2700}            # seconds per build (45 min)
CPUS=${SWEEP_CPUS:-4}           # on the server, leave the rest for the live site
SHARD=${SHARD:-0}
SHARDS=${SHARDS:-1}
PY=$(command -v python3 || command -v python)
N=$(docker run --rm -v "$HOST_DIR/engine:/app/engine_src" poe2-optimizer sh -c \
    "cp /app/engine_src/*.py /app/engine/ && cp -r /app/engine_src/tools /app/engine/ && cd /app/engine && python -c 'import sys; sys.path.insert(0,\"tools\"); from az_test import sweep_prompts; print(len(sweep_prompts()))'" 2>/dev/null | tail -1)
echo "$(date -u +%FT%TZ) sweep lane $SHARD of $SHARDS: $N builds in all, ${LIMIT}s limit each, $CPUS cpus, -> $OUT"
# On the PC, check in with the server so its status.sh shows this lane (PC_REPORT=1).
report() { [ "${PC_REPORT:-0}" = 1 ] && engine/tools/pc_report.sh "sweep-lane-$SHARD" "$*"; }
mine=$(seq 1 "$N" | awk -v s="$SHARD" -v n="$SHARDS" '(($1-1)%n)==s' | wc -l)
k=0
report "A-to-Z sweep lane $SHARD: started, $mine builds"
for i in $(seq 1 "$N"); do
  [ $(( (i - 1) % SHARDS )) -eq "$SHARD" ] || continue
  k=$((k + 1))
  report "A-to-Z sweep lane $SHARD: build $k of $mine (#$i) running"
  docker run --rm --cpus "$CPUS" --name "sweep-$SHARD-$i" -e SWEEP=1 -e WORKERS="$CPUS" \
    -v "$HOST_DIR/engine:/app/engine_src" poe2-optimizer sh -c \
    "cp /app/engine_src/*.py /app/engine_src/runner.lua /app/engine/ && cp -r /app/engine_src/tools /app/engine/ && cp /app/engine_src/data/*.json /app/engine/data/ && cd /app/engine && timeout -s KILL $LIMIT python tools/az_test.py run --only $i --out /app/engine_src/data/baseline/$OUT_NAME"
  code=$?
  if [ "$code" = 137 ]; then
    echo "#$i TIMEOUT after ${LIMIT}s"
    "$PY" - "$OUT" "$i" "$LIMIT" <<'EOF'
import json, os, sys, time
out, i, limit = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
d = json.load(open(out)) if os.path.exists(out) else {"results": {}}
d.setdefault("timeouts", {})[str(i)] = {"limit_seconds": limit, "at": time.strftime("%Y-%m-%d %H:%M")}
json.dump(d, open(out, "w"), indent=1, ensure_ascii=False)
EOF
  fi
done
echo "$(date -u +%FT%TZ) sweep lane $SHARD finished"
report "A-to-Z sweep lane $SHARD: finished all $mine builds"
