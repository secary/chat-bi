#!/bin/sh
set -eu

backend_pid=""
frontend_pid=""

term_handler() {
    if [ -n "$backend_pid" ] && kill -0 "$backend_pid" 2>/dev/null; then
        kill "$backend_pid"
    fi
    if [ -n "$frontend_pid" ] && kill -0 "$frontend_pid" 2>/dev/null; then
        kill "$frontend_pid"
    fi
}

trap term_handler INT TERM

(
    cd /app/frontend
    if [ ! -f node_modules/.install-stamp ] || [ package-lock.json -nt node_modules/.install-stamp ]; then
        echo "[frontend] package-lock.json changed - running npm ci..."
        npm ci
        touch node_modules/.install-stamp
    fi
    npm run dev -- --host 0.0.0.0 --port 5173
) &
frontend_pid="$!"

.venv/bin/uvicorn backend.main:app \
    --host 0.0.0.0 \
    --port 8226 \
    --reload \
    --reload-dir /app/backend \
    --reload-dir /app/skills &
backend_pid="$!"

while kill -0 "$backend_pid" 2>/dev/null && kill -0 "$frontend_pid" 2>/dev/null; do
    sleep 1
done

term_handler
wait "$backend_pid" 2>/dev/null || true
wait "$frontend_pid" 2>/dev/null || true
