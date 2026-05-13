#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ ! -d "${ROOT}/.git" ]]; then
  echo "Expected a Git repository at ${ROOT}, but .git was not found." >&2
  exit 1
fi

if [[ ! -f "${ROOT}/scripts/format_code.py" ]]; then
  echo "Missing scripts/format_code.py. Please run this from a complete ChatBI checkout." >&2
  exit 1
fi

log() {
  echo "[bootstrap] $1"
}

SYNC_DEPS=0
RUN_FORMAT=0

usage() {
  cat <<'USAGE'
Usage: bash scripts/bootstrap_dev.sh [--sync] [--format] [--full]

  --sync    Run uv sync and frontend npm ci.
  --format  Run scripts/format_code.py after checks.
  --full    Same as --sync --format.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --sync)
      SYNC_DEPS=1
      ;;
    --format)
      RUN_FORMAT=1
      ;;
    --full)
      SYNC_DEPS=1
      RUN_FORMAT=1
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

python_bin() {
  if [[ -x "${ROOT}/.venv/bin/python" ]]; then
    echo "${ROOT}/.venv/bin/python"
  elif [[ -x "${ROOT}/.venv/Scripts/python.exe" ]]; then
    echo "${ROOT}/.venv/Scripts/python.exe"
  fi
}

log "Configuring Git hooks path to .githooks"
git -C "${ROOT}" config core.hooksPath .githooks

if [[ ! -d "${ROOT}/.githooks" ]]; then
  log "Warning: .githooks directory is missing."
fi

if [[ "${SYNC_DEPS}" -eq 1 ]]; then
  if command -v uv >/dev/null 2>&1; then
    log "Syncing Python environment with uv"
    (cd "${ROOT}" && uv sync)
  else
    log "uv not found. Skipping Python dependency sync."
  fi

  if command -v npm >/dev/null 2>&1 && [[ -f "${ROOT}/frontend/package-lock.json" ]]; then
    log "Syncing frontend dependencies with npm ci"
    (cd "${ROOT}/frontend" && npm ci)
  else
    log "npm or frontend/package-lock.json not found. Skipping frontend dependency sync."
  fi
fi

PYTHON_BIN="$(python_bin)"
if [[ "${RUN_FORMAT}" -eq 1 && -n "${PYTHON_BIN}" ]]; then
  log "Running formatter with ${PYTHON_BIN}"
  PYTHONPATH=. "${PYTHON_BIN}" "${ROOT}/scripts/format_code.py"
elif [[ "${RUN_FORMAT}" -eq 1 ]]; then
  log "Python virtualenv not found at .venv. Skipping formatter run."
  log "Create it with: bash scripts/bootstrap_dev.sh --sync"
else
  log "Skipping formatter. Run with --format when you want local cleanup."
fi

if [[ -f "${ROOT}/.env.dev" ]]; then
  log ".env.dev found"
else
  log ".env.dev not found. Create it before local dev if you need dev-specific settings."
fi

if [[ -d "${ROOT}/frontend/node_modules" ]]; then
  log "frontend/node_modules found"
else
  log "frontend/node_modules missing. Run: cd frontend && npm ci"
fi

log "Recommended next steps:"
log "1. First setup: bash scripts/bootstrap_dev.sh --sync"
log "2. Code cleanup: bash scripts/bootstrap_dev.sh --format"
log "3. Quick tests: PYTHONPATH=INSERT INTO chatbi_logs_trace_log (
    id,
    trace_id,
    span_name,
    event_name,
    level,
    message,
    payload,
    created_at
  )
VALUES (
    'id:bigint',
    'trace_id:varchar',
    'span_name:varchar',
    'event_name:varchar',
    'level:varchar',
    'message:varchar',
    'payload:json',
    'created_at:datetime'
  );. .venv/bin/python scripts/run_tests.py foundation -- -q"
