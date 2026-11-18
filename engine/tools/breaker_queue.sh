#!/bin/bash
# Breaker job queue on the server: long unattended scans, one after another, no Claude usage.
# Progress shows in status.sh (~/server_jobs/breaker-queue.status). Results are committed and pushed at the end.
# Phone (ntfy): only when the queue finishes or a step fails, and never 10 pm - 8 am Mazatlan (then the message waits in
# ~/routines/pending.txt for the 8 am report).
#   nohup ~/phaph/engine/tools/breaker_queue.sh > ~/breaker_queue.log 2>&1 &
set -u
cd "$(dirname "$0")/../.."
CPUS=${CPUS:-6}
mkdir -p ~/server_jobs ~/routines
state() { echo "$(date '+%H:%M') $*" > ~/server_jobs/breaker-queue.status; echo "$(date -u +%FT%TZ) $*"; }
notify() {
  local h; h=$(TZ=America/Mazatlan date +%-H)
  local topic; topic=$(grep -E '^NTFY_TOPIC=' .env | cut -d= -f2)
  if [ "$h" -ge 8 ] && [ "$h" -lt 22 ] && [ -n "$topic" ]; then
    curl -s -H "Title: Whetstone" -d "$*" "https://ntfy.sh/$topic" > /dev/null
  else
    echo "$(date '+%F %H:%M') $*" >> ~/routines/pending.txt
  fi
}
run() {
  docker run --rm --cpus "$CPUS" -v "$PWD/engine:/app/engine_src" poe2-optimizer sh -c \
    "cp /app/engine_src/*.py /app/engine_src/runner.lua /app/engine/ && cp -r /app/engine_src/tools /app/engine/ && cp /app/engine_src/data/*.json /app/engine/data/ && cd /app/engine && $1"
}

# Wait for anything else heavy on the server (a Breaker day run or another scan) to finish first.
while pgrep -f breaker_day.sh > /dev/null || docker ps --format '{{.Image}} {{.Names}}' | grep -v phaph- | grep -q poe2-optimizer; do
  state "waiting for the running Breaker scan to finish"
  sleep 120
done

# Job 1: condition scan per ascendancy (each skill on its class's own weapons, with the ascendancy's passives).
OUT=engine/data/breaker/conditions_asc
mkdir -p "$OUT"
mapfile -t PAIRS < <(run "python -c 'from pob import PoB
p = PoB(); [print(c[\"name\"] + \"|\" + a) for c in p.list_classes() for a in c[\"ascendancies\"]]'" 2>/dev/null)
n=${#PAIRS[@]}; k=0; failed=0
for pair in "${PAIRS[@]}"; do
  cls=${pair%%|*}; asc=${pair#*|}; k=$((k + 1))
  file="$OUT/$(echo "$asc" | tr ' ' '_').json"
  state "condition scan per ascendancy: $k of $n ($asc)"
  if ! run "python condition_scan.py run --workers $CPUS --class '$cls' --ascendancy '$asc' --out /app/engine_src/${file#engine/}" > "$OUT/$(echo "$asc" | tr ' ' '_').log" 2>&1; then
    failed=$((failed + 1))
    notify "Breaker queue: condition scan failed for $asc (log in $OUT). The queue carries on."
  fi
done
for f in "$OUT"/*.json; do
  run "python condition_scan.py report /app/engine_src/${f#engine/}" > "${f%.json}.txt" 2>&1
done

git add "$OUT" && git -c user.name=Claude -c user.email=noreply@anthropic.com commit -q -m "Breaker: condition scan per ascendancy ($n ascendancies)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && git push -q
state "finished: condition scan per ascendancy, $n ascendancies, $failed failed"
notify "Breaker queue finished: condition scan for all $n ascendancies ($failed failed). Results pushed; details in the 8 am report."
