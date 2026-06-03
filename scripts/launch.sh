#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

APP_URL="http://localhost:5173"
COMPOSE_FILE="${ROOT}/docker-compose.prod.yml"
BUILD=1
OPEN_BROWSER=1
TIMEOUT_SECONDS=90

usage() {
  cat <<'USAGE'
Usage: bash scripts/launch.sh [options]

Run local self-checks, start the production-style ChatBI stack, wait for /health, then open the app.

Options:
  --no-build       Start existing images without rebuilding.
  --no-open        Do not open the browser after startup.
  --url URL        App URL to open and health-check. Default: http://localhost:5173
  --timeout SEC    Seconds to wait for /health. Default: 90
  -h, --help       Show this help.
USAGE
}

log() {
  echo "[start-prod] $1"
}

ensure_env_file() {
  if [[ -f "${ROOT}/.env" ]]; then
    return 0
  fi
  if [[ ! -f "${ROOT}/.env.example" ]]; then
    echo "No env file found and missing ${ROOT}/.env.example." >&2
    exit 1
  fi

  cp "${ROOT}/.env.example" "${ROOT}/.env"
  log "No env file found; copied .env.example to .env"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-build)
      BUILD=0
      ;;
    --no-open)
      OPEN_BROWSER=0
      ;;
    --url)
      if [[ $# -lt 2 ]]; then
        echo "--url requires a value." >&2
        usage >&2
        exit 2
      fi
      APP_URL="$2"
      shift
      ;;
    --timeout)
      if [[ $# -lt 2 ]]; then
        echo "--timeout requires a value." >&2
        usage >&2
        exit 2
      fi
      TIMEOUT_SECONDS="$2"
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

if ! [[ "${TIMEOUT_SECONDS}" =~ ^[0-9]+$ ]]; then
  echo "--timeout must be a non-negative integer." >&2
  exit 2
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "docker command not found. Install Docker Desktop or Docker Engine first." >&2
  exit 1
fi

if [[ ! -f "${COMPOSE_FILE}" ]]; then
  echo "Missing ${COMPOSE_FILE}. Run this from a complete ChatBI checkout." >&2
  exit 1
fi

ensure_env_file

cd "${ROOT}"

compose_cmd=(docker compose -f "${COMPOSE_FILE}")
up_cmd=("${compose_cmd[@]}" up -d)
if [[ "${BUILD}" -eq 1 ]]; then
  up_cmd+=("--build")
fi

log "Starting production stack with docker compose"
"${up_cmd[@]}"

HEALTH_URL="${APP_URL%/}/health"
if command -v curl >/dev/null 2>&1; then
  log "Waiting for ${HEALTH_URL}"
  deadline=$((SECONDS + TIMEOUT_SECONDS))
  until curl -fsS "${HEALTH_URL}" >/dev/null 2>&1; do
    if (( SECONDS >= deadline )); then
      log "Timed out waiting for ${HEALTH_URL}"
      log "Check logs with: docker compose -f docker-compose.prod.yml logs -f"
      exit 1
    fi
    sleep 2
  done
else
  log "curl not found; skipping health wait"
fi

log "ChatBI is ready at ${APP_URL}"

if [[ "${OPEN_BROWSER}" -eq 0 ]]; then
  exit 0
fi

if command -v open >/dev/null 2>&1; then
  open "${APP_URL}"
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open "${APP_URL}" >/dev/null 2>&1 &
elif command -v cmd.exe >/dev/null 2>&1; then
  cmd.exe /c start "" "${APP_URL}" >/dev/null 2>&1
else
  log "No browser opener found. Open ${APP_URL} manually."
fi
