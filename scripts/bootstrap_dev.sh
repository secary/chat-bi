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

PYTHON_BIN=""
if [[ -x "${ROOT}/.venv/bin/python" ]]; then
  PYTHON_BIN="${ROOT}/.venv/bin/python"
elif [[ -x "${ROOT}/.venv/Scripts/python.exe" ]]; then
  PYTHON_BIN="${ROOT}/.venv/Scripts/python.exe"
fi

log "Configuring Git hooks path to .githooks"
git -C "${ROOT}" config core.hooksPath .githooks

if [[ ! -d "${ROOT}/.githooks" ]]; then
  log "Warning: .githooks directory is missing."
fi

if [[ -n "${PYTHON_BIN}" ]]; then
  log "Running formatter bootstrap with ${PYTHON_BIN}"
  PYTHONPATH=. "${PYTHON_BIN}" "${ROOT}/scripts/format_code.py"
else
  log "Python virtualenv not found at .venv. Skipping formatter run."
  log "Create the project venv first, then run: PYTHONPATH=. .venv/bin/python scripts/format_code.py"
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
log "1. PYTHONPATH=. .venv/bin/python scripts/run_tests.py foundation -- -q"
log "2. cd frontend && npm run lint && npm run test"
