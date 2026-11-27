#!/bin/bash
# Task 40: Lodestone's scans on an old patch's PoB (checkouts in ~/oldpob/<tag>), graded against
# data/breaker/answer_key.json. Usage: old_patch.sh <workers> <tag>...   (resumable) -> data/breaker/old/<tag>_*.json
# The engine is the frozen copy in ~/phaph_grade (git worktree at 1820188), so fixes merged meanwhile don't split the grade.
# ENGINE_DIR / OLD_DIR / OLD_LOG override the frozen engine, the output folder and the log (task 51's re-grade).
W=$1; shift
E=${ENGINE_DIR:-$HOME/phaph_grade}; O=$HOME/phaph/engine/data/breaker/${OLD_DIR:-old}; L=$HOME/${OLD_LOG:-old_patch.log}
mkdir -p "$O"
for t in "$@"; do
  for s in ${SCANS:-condition matrix}; do
    docker run --rm --cpus "$W" --cpu-shares 128 --user 0 -v "$E"/engine:/app/engine_src:ro -v "$O":/out -v ~/oldpob:/old:ro poe2-optimizer sh -c "cp /app/engine_src/*.py /app/engine_src/runner.lua /app/engine/ && cp /app/engine_src/data/*.json /app/engine/data/ && mv /app/engine/vendor/PathOfBuilding-PoE2 /tmp/cur && cp -r /old/$t /app/engine/vendor/PathOfBuilding-PoE2 && cd /app/engine && python ${s}_scan.py run --workers $W --out /out/${t}_$s.json; chown -R $(id -u):$(id -g) /out" >> ~/old_patch_$t.log 2>&1
    echo "$t $s done $(date)" >> "$L"
  done
done
