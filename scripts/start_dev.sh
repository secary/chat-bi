#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

BACKEND_PORT="${BACKEND_PORT:-8226}"
FRONTEND_PORT="${FRONTEND_PORT:-5174}"
INIT_DB=1
DB_ONLY=0
SYNC_DEPS=1

usage() {
  cat <<'USAGE'
Usage: bash scripts/start_dev.sh [options]

Start ChatBI for local host development: MySQL, backend, and frontend all on host.

Options:
  --db-only          Initialize/check only the local dev MySQL database.
  --no-db           Do not initialize/check the local dev MySQL database.
  --no-deps         Do not auto-sync missing Python/frontend dependencies.
  --backend-port N  Backend port. Default: 8226.
  --frontend-port N Frontend port. Default: 5174.
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
    echo "Missing ${env_file}. Create it before starting local dev." >&2
    exit 1
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

env_value() {
  local key="$1"
  printf '%s' "${!key:-}"
}

truthy() {
  local value
  value="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"
  case "${value}" in
    1|true|yes|on)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

configure_git_hooks() {
  if [[ ! -d "${ROOT}/.git" ]]; then
    return 0
  fi
  if command -v git >/dev/null 2>&1; then
    git -C "${ROOT}" config core.hooksPath .githooks
  fi
  if [[ ! -d "${ROOT}/.githooks" ]]; then
    log "Warning: .githooks directory is missing."
  fi
}

sync_missing_dependencies() {
  local needs_python=0
  local needs_frontend=0

  if ! python_bin >/dev/null 2>&1; then
    needs_python=1
  fi
  if [[ ! -d "${ROOT}/frontend/node_modules" ]]; then
    needs_frontend=1
  fi
  if [[ "${needs_python}" -eq 0 && "${needs_frontend}" -eq 0 ]]; then
    return 0
  fi

  if [[ "${needs_python}" -eq 1 ]]; then
    if ! command -v uv >/dev/null 2>&1; then
      echo "Python virtualenv missing and uv command not found. Install uv or run dependency setup manually." >&2
      exit 1
    fi
    log "Python virtualenv missing; running uv sync"
    (cd "${ROOT}" && uv sync)
  fi

  if [[ "${needs_frontend}" -eq 1 ]]; then
    if ! command -v npm >/dev/null 2>&1; then
      echo "frontend/node_modules missing and npm command not found. Install Node.js/npm first." >&2
      exit 1
    fi
    if [[ ! -f "${ROOT}/frontend/package-lock.json" ]]; then
      echo "frontend/package-lock.json missing. Cannot run npm ci." >&2
      exit 1
    fi
    log "frontend/node_modules missing; running npm ci"
    (cd "${ROOT}/frontend" && npm ci)
  fi
}

seed_env_db_connections() {
  local db_name="$1"
  local idx name host port username password database_name is_default default_value
  local name_literal host_literal username_literal password_literal database_literal

  for idx in $(seq 1 20); do
    name="$(env_value "CHATBI_DB_CONNECTION_${idx}_NAME")"
    host="$(env_value "CHATBI_DB_CONNECTION_${idx}_HOST")"
    username="$(env_value "CHATBI_DB_CONNECTION_${idx}_USER")"
    database_name="$(env_value "CHATBI_DB_CONNECTION_${idx}_DATABASE")"
    if [[ -z "${name}" && -z "${host}" && -z "${username}" && -z "${database_name}" ]]; then
      continue
    fi
    port="$(env_value "CHATBI_DB_CONNECTION_${idx}_PORT")"
    password="$(env_value "CHATBI_DB_CONNECTION_${idx}_PASSWORD")"
    default_value="$(env_value "CHATBI_DB_CONNECTION_${idx}_DEFAULT")"
    port="${port:-3306}"

    if [[ -z "${name}" || -z "${host}" || -z "${username}" || -z "${database_name}" ]]; then
      echo "CHATBI_DB_CONNECTION_${idx} requires NAME, HOST, USER, and DATABASE." >&2
      exit 2
    fi
    if ! [[ "${port}" =~ ^[0-9]+$ ]]; then
      echo "CHATBI_DB_CONNECTION_${idx}_PORT must be a number." >&2
      exit 2
    fi
    validate_mysql_name "CHATBI_DB_CONNECTION_${idx}_DATABASE" "${database_name}"
    is_default=0
    if truthy "${default_value}"; then
      is_default=1
    fi

    name_literal="$(sql_literal "${name}")"
    host_literal="$(sql_literal "${host}")"
    username_literal="$(sql_literal "${username}")"
    password_literal="$(sql_literal "${password}")"
    database_literal="$(sql_literal "${database_name}")"

    if [[ "${is_default}" -eq 1 ]]; then
      "${SEED_ADMIN_MYSQL[@]}" "${db_name}" -e "UPDATE admin_db_connection SET is_default = 0;"
    fi
    "${SEED_ADMIN_MYSQL[@]}" "${db_name}" <<SQL
INSERT INTO admin_db_connection
  (name, host, port, username, password, database_name, is_default)
VALUES
  (${name_literal}, ${host_literal}, ${port}, ${username_literal}, ${password_literal}, ${database_literal}, ${is_default})
ON DUPLICATE KEY UPDATE
  host = VALUES(host),
  port = VALUES(port),
  username = VALUES(username),
  password = VALUES(password),
  database_name = VALUES(database_name),
  is_default = VALUES(is_default);
SQL
    log "Loaded env database connection: ${name}"
  done
}

seed_env_app_users() {
  if [[ -z "${CHATBI_SEED_USERS:-}" ]]; then
    return 0
  fi

  local seed_python
  seed_python="$(python_bin || true)"
  if [[ -z "${seed_python}" ]]; then
    log "Python virtualenv missing; skipping env seed users"
    return 0
  fi

  log "Refreshing env seed users"
  (
    cd "${ROOT}"
    export PYTHONPATH=.
    export CHATBI_SEED_USERS_RESET_PASSWORD="${CHATBI_SEED_USERS_RESET_PASSWORD:-true}"
    export CHATBI_SEED_USERS_PRUNE="${CHATBI_SEED_USERS_PRUNE:-true}"
    "${seed_python}" - <<'PY'
from backend.config import Settings
from backend.default_admin_seed import seed_startup_users

results = seed_startup_users(Settings())
if "failed" in results:
    raise SystemExit("env seed users failed")
print("Seed users:", ", ".join(results) if results else "none")
PY
  )
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

  local table_count
  table_count="$(
    "${app_mysql[@]}" "${CHATBI_DB_NAME}" -N -s -e \
      "SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA = $(sql_literal "${CHATBI_DB_NAME}")"
  )"
  if [[ "${table_count:-0}" != "0" ]]; then
    log "Local MySQL database already contains tables; skipping database/init.sql"
  else
    log "Importing database/init.sql"
    "${admin_mysql[@]}" "${CHATBI_DB_NAME}" < <(
      sed "s/chatbi_demo/${CHATBI_DB_NAME}/g" "${ROOT}/database/init.sql"
    )
  fi

  SEED_ADMIN_MYSQL=("${admin_mysql[@]}")
  seed_env_db_connections "${CHATBI_DB_NAME}"
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
      --no-deps)
        SYNC_DEPS=0
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

if [[ "${DB_ONLY}" -eq 0 && "${SYNC_DEPS}" -eq 1 ]]; then
  configure_git_hooks
  sync_missing_dependencies
fi

if [[ "${INIT_DB}" -eq 1 ]]; then
  init_local_mysql
  seed_env_app_users
fi

if [[ "${DB_ONLY}" -eq 1 ]]; then
  log "Local dev MySQL is ready on ${CHATBI_DB_HOST:-127.0.0.1}:${CHATBI_DB_PORT:-3306}"
  exit 0
fi

PYTHON_BIN="$(python_bin || true)"
if [[ -z "${PYTHON_BIN}" ]]; then
  echo "Python virtualenv not found. Run: bash scripts/start_dev.sh" >&2
  exit 1
fi

if [[ ! -d "${ROOT}/frontend/node_modules" ]]; then
  echo "frontend/node_modules missing. Run: bash scripts/start_dev.sh" >&2
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
  export CHATBI_SEED_USERS_RESET_PASSWORD="${CHATBI_SEED_USERS_RESET_PASSWORD:-true}"
  export CHATBI_SEED_USERS_PRUNE="${CHATBI_SEED_USERS_PRUNE:-true}"
  "${PYTHON_BIN}" -m uvicorn backend.main:app --reload --host 127.0.0.1 --port "${BACKEND_PORT}"
) &
backend_pid="$!"

log "Starting frontend on http://localhost:${FRONTEND_PORT}"
(
  cd "${ROOT}/frontend"
  export VITE_PROXY_TARGET="${VITE_PROXY_TARGET:-http://127.0.0.1:${BACKEND_PORT}}"
  export VITE_AUTH_ENABLED="${VITE_AUTH_ENABLED:-${CHATBI_AUTH_ENABLED:-false}}"
  npm run dev -- --host 0.0.0.0 --port "${FRONTEND_PORT}"
) &
frontend_pid="$!"

log "Press Ctrl+C to stop backend and frontend. Dev MySQL stays running."

while kill -0 "${backend_pid}" >/dev/null 2>&1 && kill -0 "${frontend_pid}" >/dev/null 2>&1; do
  sleep 1
done

wait "${backend_pid}" || true
wait "${frontend_pid}" || true
