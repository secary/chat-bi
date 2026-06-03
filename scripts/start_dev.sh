#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
START_DB=1
DB_ONLY=0

usage() {
  cat <<'USAGE'
Usage: bash scripts/start_dev.sh [options]

Start ChatBI for local host development: MySQL in Docker, backend and frontend on host.

Options:
  --db-only          Start only the dev MySQL container.
  --no-db           Do not start the dev MySQL container.
  --backend-port N  Backend port. Default: 8000.
  --frontend-port N Frontend port. Default: 5173.
  -h, --help        Show this help.
USAGE
}

log() {
  echo "[dev] $1"
}

python_bin() {
  if [[ -x "${ROOT}/.venv/bin/python" ]]; then
    echo "${ROOT}/.venv/bin/python"
  elif [[ -x "${ROOT}/.venv/Scripts/python.exe" ]]; then
    echo "${ROOT}/.venv/Scripts/python.exe"
  else
    return 1
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --db-only)
      DB_ONLY=1
      ;;
    --no-db)
      START_DB=0
      ;;
    --backend-port)
      if [[ $# -lt 2 ]]; then
        echo "--backend-port requires a value." >&2
        usage >&2
        exit 2
      fi
      BACKEND_PORT="$2"
      shift
      ;;
    --frontend-port)
      if [[ $# -lt 2 ]]; then
        echo "--frontend-port requires a value." >&2
        usage >&2
        exit 2
      fi
      FRONTEND_PORT="$2"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

if ! [[ "${BACKEND_PORT}" =~ ^[0-9]+$ && "${FRONTEND_PORT}" =~ ^[0-9]+$ ]]; then
  echo "Ports must be non-negative integers." >&2
  exit 2
fi

if [[ "${START_DB}" -eq 1 ]]; then
  if ! command -v docker >/dev/null 2>&1; then
    echo "docker command not found. Install Docker Desktop or Docker Engine first." >&2
    exit 1
  fi
  log "Starting dev MySQL container"
  compose_cmd=(docker compose)
  if [[ -f "${ROOT}/.env.dev" ]]; then
    compose_cmd+=(--env-file "${ROOT}/.env.dev")
  fi
  compose_cmd+=(-f "${ROOT}/docker-compose.dev.yml")
  "${compose_cmd[@]}" up -d chatbi-db-dev
fi

if [[ "${DB_ONLY}" -eq 1 ]]; then
  log "Dev MySQL is ready on 127.0.0.1:33067"
  exit 0
fi

PYTHON_BIN="$(python_bin || true)"
if [[ -z "${PYTHON_BIN}" ]]; then
  echo "Python virtualenv not found. Run: bash scripts/bootstrap_dev.sh --sync" >&2
  exit 1
fi

if [[ ! -d "${ROOT}/frontend/node_modules" ]]; then
  echo "frontend/node_modules missing. Run: bash scripts/bootstrap_dev.sh --sync" >&2
  exit 1
fi

backend_pid=""
frontend_pid=""

cleanup() {
  if [[ -n "${backend_pid}" ]] && kill -0 "${backend_pid}" >/dev/null 2>&1; then
    kill "${backend_pid}" >/dev/null 2>&1 || true
  fi
  if [[ -n "${frontend_pid}" ]] && kill -0 "${frontend_pid}" >/dev/null 2>&1; then
    kill "${frontend_pid}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

log "Starting backend on http://127.0.0.1:${BACKEND_PORT}"
(
  cd "${ROOT}"
  export PYTHONPATH=.
  export CHATBI_AUTH_ENABLED="${CHATBI_AUTH_ENABLED:-false}"
  "${PYTHON_BIN}" -m uvicorn backend.main:app --reload --host 127.0.0.1 --port "${BACKEND_PORT}"
) &
backend_pid="$!"

log "Starting frontend on http://localhost:${FRONTEND_PORT}"
(
  cd "${ROOT}/frontend"
  export VITE_PROXY_TARGET="${VITE_PROXY_TARGET:-http://127.0.0.1:${BACKEND_PORT}}"
  export VITE_AUTH_ENABLED="${VITE_AUTH_ENABLED:-false}"
  npm run dev -- --host 0.0.0.0 --port "${FRONTEND_PORT}"
) &
frontend_pid="$!"

log "Press Ctrl+C to stop backend and frontend. Dev MySQL stays running."

while kill -0 "${backend_pid}" >/dev/null 2>&1 && kill -0 "${frontend_pid}" >/dev/null 2>&1; do
  sleep 1
done

wait "${backend_pid}" || true
wait "${frontend_pid}" || true
