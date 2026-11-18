#!/bin/bash
# What is running where: the server's own work plus the latest check-in from each job on Kyle's PC.
# Run on the server (ssh whetstone ~/phaph/engine/tools/status.sh, or ask the "Whetstone server" session for "status").
# PC jobs check in with engine/tools/pc_report.sh; a PC job with no news for 30+ minutes probably stopped
# (PC off or power cut). Results of PC jobs land in the repo (pushed) when they finish.
now=$(date +%s)
echo "== Server ($(hostname), $(TZ=America/Mazatlan date '+%a %H:%M') Mazatlan)"
echo "load $(cut -d' ' -f1-3 /proc/loadavg) on $(nproc) cores"
docker ps --format '  {{.Names}}: {{.Status}}' | sed 's/phaph-app-1/live site engine (phaph-app-1)/; s/phaph-tunnel-1/live site tunnel (phaph-tunnel-1)/'
active=$(docker exec phaph-app-1 python -c "import sqlite3;c=sqlite3.connect('/data/jobs.sqlite3');print(c.execute(\"select count(*) from jobs where status in ('queued','running')\").fetchone()[0])" 2>/dev/null)
echo "  player builds running or queued: ${active:-?}"
pgrep -f "claude -p" >/dev/null && echo "  a scheduled Claude routine is running (morning report / research)"
tmux has-session -t whetstone 2>/dev/null && echo "  Claude session 'Whetstone server' (Remote Control) is up"
echo "  scheduled: $(crontab -l 2>/dev/null | grep -c routines/) routine(s): $(crontab -l 2>/dev/null | grep -o 'routines/[a-z_]*' | tr '\n' ' ')"
shopt -s nullglob
for f in ~/server_jobs/*.status; do echo "  $(basename "$f" .status): $(cat "$f")"; done
[ -s ~/routines/pending.txt ] && echo "  waiting for the 8 am report: $(wc -l < ~/routines/pending.txt) message(s) held back in quiet hours"
echo
echo "== Kyle's PC (last check-in per job)"
shopt -s nullglob
files=(~/pc_jobs/*.status)
[ ${#files[@]} -eq 0 ] && echo "  no PC jobs have checked in"
for f in "${files[@]}"; do
  age=$(( (now - $(stat -c %Y "$f")) / 60 ))
  state=$(cat "$f")
  flag=""
  case "$state" in *finished*|*stopped*) ;; *) [ "$age" -ge 30 ] && flag="  <- no news for ${age} min: PC off or job stuck?";; esac
  echo "  $(basename "$f" .status): $state (${age} min ago)$flag"
done
