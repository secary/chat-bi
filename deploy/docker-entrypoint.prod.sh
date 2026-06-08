#!/bin/sh
set -eu

uvicorn_pid=""
nginx_pid=""

term_handler() {
    if [ -n "$uvicorn_pid" ] && kill -0 "$uvicorn_pid" 2>/dev/null; then
        kill "$uvicorn_pid"
    fi
    if [ -n "$nginx_pid" ] && kill -0 "$nginx_pid" 2>/dev/null; then
        nginx -s quit 2>/dev/null || kill "$nginx_pid"
    fi
}

trap term_handler INT TERM

.venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8226 &
uvicorn_pid="$!"

nginx -g "daemon off;" &
nginx_pid="$!"

while kill -0 "$uvicorn_pid" 2>/dev/null && kill -0 "$nginx_pid" 2>/dev/null; do
    sleep 1
done

term_handler
wait "$nginx_pid" 2>/dev/null || true
wait "$uvicorn_pid" 2>/dev/null || true
