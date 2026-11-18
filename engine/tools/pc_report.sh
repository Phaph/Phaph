#!/bin/bash
# A PC job checks in with the server, so `status.sh` on the server shows what the PC is doing.
#   engine/tools/pc_report.sh <job-name> "<one-line state>"
# Uses the `whetstone` SSH host (key in ~/.ssh/whetstone_vps). Never fails the job if the server can't be reached.
job=$1; shift
msg="$(date '+%H:%M') $*"
ssh -o BatchMode=yes -o ConnectTimeout=8 -o LogLevel=ERROR whetstone \
  "mkdir -p ~/pc_jobs && printf '%s\n' $(printf '%q' "$msg") > ~/pc_jobs/$job.status" 2>/dev/null || true
