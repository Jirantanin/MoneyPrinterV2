#!/usr/bin/env bash
set -euo pipefail

PORT=8899
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[restart] Killing any process on port $PORT..."
PID=$(netstat -aon 2>/dev/null | grep ":${PORT} " | awk '{print $5}' | head -1 || true)
if [[ -n "$PID" && "$PID" != "0" ]]; then
    taskkill //F //PID "$PID" > /dev/null 2>&1 && echo "[restart] Killed PID $PID" || true
else
    echo "[restart] No process found on port $PORT"
fi

echo "[restart] Starting Studio..."
cd "$ROOT"
source venv/Scripts/activate
py -c "from src.podcast_server import launch_podcast_server; launch_podcast_server()"
