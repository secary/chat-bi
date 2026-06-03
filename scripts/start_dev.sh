#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
INIT_DB=1
DB_ONLY=0

usage() {
  cat <<'USAGE'
Usage: bash scripts/start_dev.sh [options]

Start ChatBI for local host development: MySQL, backend, and frontend all on host.

Options:
  --db-only          Initialize/check only the local dev MySQL database.
  --no-db           Do not initialize/check the local dev MySQL database.
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

load_env_file() {
  local env_file="$1"
  if [[ ! -f "${env_file}" ]]; then
    return 0
  fi

  while IFS='=' read -r raw_key raw_value || [[ -n "${raw_key}" ]]; do
    raw_key="${raw_key#"${raw_key%%[![:space:]]*}"}"
    raw_key="${raw_key%"${raw_key##*[![:space:]]}"}"
    if [[ -z "${raw_key}" || "${raw_key}" == \#* ]]; then
      continue
    fi
    if ! [[ "${raw_key}" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
      continue
    fi
    export "${raw_key}=${raw_value}"
  done <"${env_file}"
}

sql_literal() {
  local value="$1"
  value="${value//\\/\\\\}"
  value="${value//\'/\'\'}"
  printf "'%s'" "${value}"
}

validate_mysql_name() {
  local label="$1"
  local value="$2"
  if ! [[ "${value}" =~ ^[A-Za-z0-9_]+$ ]]; then
    echo "${label} must contain only letters, numbers, and underscores." >&2
    exit 2
  fi
}

init_local_mysql() {
  if ! command -v mysql >/dev/null 2>&1; then
    echo "mysql command not found. Install MySQL client first." >&2
    exit 1
  fi

  CHATBI_DB_HOST="${CHATBI_DB_HOST:-127.0.0.1}"
  CHATBI_DB_PORT="${CHATBI_DB_PORT:-3306}"
  CHATBI_DB_NAME="${CHATBI_DB_NAME:-chatbi_demo}"
  CHATBI_DB_USER="${CHATBI_DB_USER:-demo_user}"
  CHATBI_DB_PASSWORD="${CHATBI_DB_PASSWORD:-demo_pass}"
  CHATBI_MYSQL_ADMIN_USER="${CHATBI_MYSQL_ADMIN_USER:-root}"

  validate_mysql_name "CHATBI_DB_NAME" "${CHATBI_DB_NAME}"
  validate_mysql_name "CHATBI_DB_USER" "${CHATBI_DB_USER}"

  local password_literal user_literal
  local admin_mysql=(
    mysql
    --protocol=TCP
    -h "${CHATBI_DB_HOST}"
    -P "${CHATBI_DB_PORT}"
    -u "${CHATBI_MYSQL_ADMIN_USER}"
  )
  local app_mysql=(
    mysql
    --protocol=TCP
    -h "${CHATBI_DB_HOST}"
    -P "${CHATBI_DB_PORT}"
    -u "${CHATBI_DB_USER}"
    "-p${CHATBI_DB_PASSWORD}"
  )
  if [[ -n "${CHATBI_MYSQL_ADMIN_PASSWORD:-}" ]]; then
    admin_mysql+=("-p${CHATBI_MYSQL_ADMIN_PASSWORD}")
  fi
  password_literal="$(sql_literal "${CHATBI_DB_PASSWORD}")"
  user_literal="$(sql_literal "${CHATBI_DB_USER}")"

  log "Initializing local MySQL database ${CHATBI_DB_NAME} on ${CHATBI_DB_HOST}:${CHATBI_DB_PORT}"
  "${admin_mysql[@]}" <<SQL
CREATE DATABASE IF NOT EXISTS \`${CHATBI_DB_NAME}\`
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS ${user_literal}@'localhost' IDENTIFIED BY ${password_literal};
CREATE USER IF NOT EXISTS ${user_literal}@'%' IDENTIFIED BY ${password_literal};
ALTER USER ${user_literal}@'localhost' IDENTIFIED BY ${password_literal};
ALTER USER ${user_literal}@'%' IDENTIFIED BY ${password_literal};
GRANT ALL PRIVILEGES ON \`${CHATBI_DB_NAME}\`.* TO ${user_literal}@'localhost';
GRANT ALL PRIVILEGES ON \`${CHATBI_DB_NAME}\`.* TO ${user_literal}@'%';
FLUSH PRIVILEGES;
SQL

  if "${app_mysql[@]}" "${CHATBI_DB_NAME}" -N -s -e "SELECT 1 FROM app_user LIMIT 1" >/dev/null 2>&1; then
    log "Local MySQL database already initialized"
    return 0
  fi

  log "Importing database/init.sql"
  "${admin_mysql[@]}" "${CHATBI_DB_NAME}" <"${ROOT}/database/init.sql"
}

load_env_file "${ROOT}/.env.dev"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --db-only)
      DB_ONLY=1
      ;;
    --no-db)
      INIT_DB=0
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

if [[ "${INIT_DB}" -eq 1 ]]; then
  init_local_mysql
fi

if [[ "${DB_ONLY}" -eq 1 ]]; then
  log "Local dev MySQL is ready on ${CHATBI_DB_HOST:-127.0.0.1}:${CHATBI_DB_PORT:-3306}"
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
