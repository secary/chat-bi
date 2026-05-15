#!/bin/sh
set -e

# Host bind-mount + named node_modules volume: rebuild image alone does not refresh deps.
if [ ! -f node_modules/.install-stamp ] || [ package-lock.json -nt node_modules/.install-stamp ]; then
  echo "[frontend] package-lock.json changed — running npm ci..."
  npm ci
  touch node_modules/.install-stamp
fi

exec npm run dev -- --host 0.0.0.0
