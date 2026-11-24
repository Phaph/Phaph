#!/bin/bash
# Breaker job queue on the server: long unattended scans, one after another, no Claude usage.
# Run it from its own clone (~/breaker), never from ~/phaph, where the interactive "Whetstone server" session works:
#   git clone -b <branch> git@github.com:Phaph/Phaph.git ~/breaker   (once), then  cd ~/breaker && git pull
#   cd ~/breaker && JOBS="matrix_asc sweep" nohup engine/tools/breaker_queue.sh > ~/breaker_queue.log 2>&1 &
# Jobs (run in the order given in JOBS):
#   conditions_asc  condition scan per ascendancy        (~6 h)  engine/data/breaker/conditions_asc/
#   matrix          unique/keystone x skill matrix       (~1 h)  engine/data/breaker/matrix.json
#   matrix_asc      the matrix per ascendancy, own weapons and ascendancy passives (~10-15 h)
#   blind           blind test: the search per ascendancy vs poe.ninja's ladder (tools/blind_test.py, ~12 h)
#                                                               engine/data/breaker/matrix_asc/
#   sweep           A-to-Z sweep, one build per ascendancy (~17 h on the server) engine/data/baseline/az_sweep_server.json
# Progress shows in status.sh (~/server_jobs/breaker-queue.status); each job's results are committed and pushed as it
# finishes. Background containers get low CPU priority (~/routines/priority.sh), so player builds come first.
# Phone (ntfy): when the queue finishes or a job fails, never 10 pm - 8 am Mazatlan (then the message waits in
# ~/routines/pending.txt for the 8 am report).
set -u
cd "$(dirname "$0")/../.."
CPUS=${CPUS:-6}
JOBS=${JOBS:-"conditions_asc matrix"}
mkdir -p ~/server_jobs ~/routines
state() { echo "$(date '+%H:%M') $*" > ~/server_jobs/breaker-queue.status; echo "$(date -u +%FT%TZ) $*"; }
notify() {
  local h; h=$(TZ=America/Mazatlan date +%-H)
  local topic; topic=$(grep -hE '^NTFY_TOPIC=' .env ~/phaph/.env 2>/dev/null | head -1 | cut -d= -f2)
  if [ "$h" -ge 8 ] && [ "$h" -lt 22 ] && [ -n "$topic" ]; then
    curl -s -H "Title: Whetstone" -d "$*" "https://ntfy.sh/$topic" > /dev/null
  else
    echo "$(date '+%F %H:%M') $*" >> ~/routines/pending.txt
  fi
}
run() {
  docker run --rm --cpus "$CPUS" --cpu-shares 128 -v "$PWD/engine:/app/engine_src" poe2-optimizer sh -c \
    "cp /app/engine_src/*.py /app/engine_src/runner.lua /app/engine/ && cp -r /app/engine_src/tools /app/engine/ && cp /app/engine_src/data/*.json /app/engine/data/ && cd /app/engine && $1"
}
save() {   # commit only this job's files, then push (rebasing on whatever else was pushed meanwhile)
  local msg=$1; shift
  git add "$@" && git -c user.name=Claude -c user.email=noreply@anthropic.com commit -q -m "$msg

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- "$@" && git pull -q --rebase && git push -q
}
ascendancies() {
  run "python -c 'from pob import PoB
p = PoB(); [print(c[\"name\"] + \"|\" + a) for c in p.list_classes() for a in c[\"ascendancies\"]]'" 2>/dev/null
}
failed=0

# Wait for anything else heavy on the server (a Breaker day run or another scan) to finish first.
# By name, not image: a rebuild leaves running containers with a bare image id (2026-11-24: the sweep started on top).
while pgrep -f breaker_day.sh > /dev/null || docker ps --format '{{.Names}}' | grep -v '^phaph-' | grep -q .; do
  state "waiting for the running Breaker scan to finish"
  sleep 120
done

per_asc() {   # $1 job label, $2 output dir, $3 scan script
  local label=$1 out=$2 script=$3 n k=0
  mkdir -p "$out"
  mapfile -t PAIRS < <(ascendancies)
  n=${#PAIRS[@]}
  for pair in "${PAIRS[@]}"; do
    local cls=${pair%%|*} asc=${pair#*|} f
    k=$((k + 1)); f="$out/$(echo "$asc" | tr ' ' '_')"
    state "$label: $k of $n ($asc)"
    if ! run "python $script run --workers $CPUS --class '$cls' --ascendancy '$asc' --out /app/engine_src/${f#engine/}.json" > "$f.log" 2>&1; then
      failed=$((failed + 1)); notify "Breaker queue: $label failed for $asc (log in $out). The queue carries on."
    fi
    run "python $script report /app/engine_src/${f#engine/}.json" > "$f.txt" 2>&1
  done
  save "Breaker: $label ($n ascendancies)" "$out"
}

for job in $JOBS; do
  case $job in
    conditions_asc) per_asc "condition scan per ascendancy" engine/data/breaker/conditions_asc condition_scan.py ;;
    matrix_asc)     per_asc "unique/keystone x skill matrix per ascendancy" engine/data/breaker/matrix_asc matrix_scan.py ;;
    matrix)
      state "unique and keystone x skill matrix: running"
      if run "python matrix_scan.py run --workers $CPUS --out /app/engine_src/data/breaker/matrix.json" > engine/data/breaker/matrix.log 2>&1; then
        run "python matrix_scan.py report /app/engine_src/data/breaker/matrix.json" > engine/data/breaker/matrix.txt 2>&1
        save "Breaker: unique and keystone x skill matrix" engine/data/breaker/matrix.json engine/data/breaker/matrix.txt
      else
        failed=$((failed + 1)); notify "Breaker queue: the unique x skill matrix failed (engine/data/breaker/matrix.log)."
      fi ;;
    sweep)
      state "A-to-Z sweep on the server: running"
      rm -f engine/data/baseline/az_sweep_server.json
      # SWEEP_SHARD / SWEEP_SHARDS: one share of the ascendancies (the nightly rotation, Kyle 2026-11-23); default all.
      SHARD=${SWEEP_SHARD:-0} SHARDS=${SWEEP_SHARDS:-1} SWEEP_CPUS=$CPUS OUT_NAME=az_sweep_server.json \
        engine/tools/night_sweep.sh > engine/data/baseline/az_sweep_server.log 2>&1
      save "A-to-Z sweep on the server" engine/data/baseline/az_sweep_server.json engine/data/baseline/az_sweep_server.log ;;
    blind)
      state "blind test vs poe.ninja (search per ascendancy): running"
      if run "python tools/blind_test.py run --workers $CPUS --out /app/engine_src/data/breaker/blind.json" > engine/data/breaker/blind.log 2>&1; then
        run "python tools/blind_test.py report /app/engine_src/data/breaker/blind.json" > engine/data/breaker/blind.txt 2>&1
        save "Lodestone: blind test vs poe.ninja" engine/data/breaker/blind.json engine/data/breaker/blind.txt
      else
        failed=$((failed + 1)); notify "Breaker queue: the blind test failed (engine/data/breaker/blind.log)."
      fi ;;
    *) state "unknown job $job, skipped" ;;
  esac
done

state "finished: $JOBS ($failed failed)"
notify "Breaker queue finished: $JOBS ($failed failed). Results pushed; details in the 8 am report."
