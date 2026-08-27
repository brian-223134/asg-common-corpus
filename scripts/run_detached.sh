#!/usr/bin/env bash
# Run a common-corpus command detached from the SSH session (survives disconnect).
# Usage: scripts/run_detached.sh mirror
# Logs: logs/<cmd>_<ts>.nohup.log (stdout/stderr) + logs/<cmd>_<ts>.log (structured, from the CLI)
set -euo pipefail
cd "$(dirname "$0")/.."
PY=/data2/chanjoong/miniforge3/envs/asg-corpus/bin/python
CMD="$1"; shift || true
TS=$(date +%Y%m%d_%H%M%S)
mkdir -p logs
setsid nohup "$PY" -m common_corpus.cli "$CMD" "$@" > "logs/${CMD}_${TS}.nohup.log" 2>&1 < /dev/null &
echo $! > "logs/${CMD}_${TS}.pid"
echo "started $CMD pid=$(cat logs/${CMD}_${TS}.pid) log=logs/${CMD}_${TS}.nohup.log"
