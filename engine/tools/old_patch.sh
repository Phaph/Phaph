#!/bin/bash
# Task 40: Lodestone's scans on an old patch's PoB (checkouts in ~/oldpob/<tag>), graded against
# data/breaker/answer_key.json. Usage: old_patch.sh <workers> <tag>...   (resumable) -> data/breaker/old/<tag>_*.json
W=$1; shift
mkdir -p ~/phaph/engine/data/breaker/old
for t in "$@"; do
  for s in ${SCANS:-condition matrix}; do
    docker run --rm --cpus "$W" --cpu-shares 128 --user 0 -v ~/phaph/engine:/app/engine_src -v ~/oldpob:/old:ro poe2-optimizer sh -c "cp /app/engine_src/*.py /app/engine_src/runner.lua /app/engine/ && cp /app/engine_src/data/*.json /app/engine/data/ && mv /app/engine/vendor/PathOfBuilding-PoE2 /tmp/cur && cp -r /old/$t /app/engine/vendor/PathOfBuilding-PoE2 && cd /app/engine && python ${s}_scan.py run --workers $W --out /app/engine_src/data/breaker/old/${t}_$s.json; chown -R $(id -u):$(id -g) /app/engine_src/data/breaker/old" >> ~/old_patch_$t.log 2>&1
    echo "$t $s done $(date)" >> ~/old_patch.log
  done
done
