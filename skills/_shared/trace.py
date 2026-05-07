from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from typing import Any, Dict, Optional


MAX_PAYLOAD_LENGTH = 6000


def log_skill_event(
    span_name: str,
    event_name: str,
    message: str = "",
    payload: Optional[Dict[str, Any]] = None,
    level: str = "INFO",
) -> None:
    trace_id = os.getenv("CHATBI_TRACE_ID", "").strip()
    if not trace_id:
        return
    try:
        _run_sql(_create_trace_db_sql())
        _run_sql(_create_trace_table_sql(), database=_log_db_name())
        _run_sql(
            "INSERT INTO chatbi_trace_log "
            "(trace_id, span_name, event_name, level, message, payload, created_at) "
            f"VALUES ({_quote(trace_id)}, {_quote(span_name)}, {_quote(event_name)}, "
            f"{_quote(level)}, {_quote(message[:500])}, "
            f"CAST({_quote(_payload_json(payload))} AS JSON), {_quote(_now())});",
            database=_log_db_name(),
        )
    except Exception:
        return


def _log_db_name() -> str:
    return os.getenv("CHATBI_LOG_DB_NAME", "chatbi_logs")


def _log_db_config() -> Dict[str, str]:
    return {
        "host": os.getenv("CHATBI_LOG_DB_HOST", os.getenv("CHATBI_DB_HOST", "127.0.0.1")),
        "port": os.getenv("CHATBI_LOG_DB_PORT", os.getenv("CHATBI_DB_PORT", "3307")),
        "user": os.getenv("CHATBI_LOG_DB_USER", os.getenv("CHATBI_DB_USER", "demo_user")),
        "password": os.getenv(
            "CHATBI_LOG_DB_PASSWORD", os.getenv("CHATBI_DB_PASSWORD", "demo_pass")
        ),
    }


def _create_trace_db_sql() -> str:
    return f"""
CREATE DATABASE IF NOT EXISTS `{_safe_ident(_log_db_name())}`
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;
""".strip()


def _create_trace_table_sql() -> str:
    return """
CREATE TABLE IF NOT EXISTS chatbi_trace_log (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  trace_id VARCHAR(64) NOT NULL,
  span_name VARCHAR(80) NOT NULL,
  event_name VARCHAR(80) NOT NULL,
  level VARCHAR(20) NOT NULL,
  message VARCHAR(500) NOT NULL,
  payload JSON NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  KEY idx_trace_log_trace_id (trace_id),
  KEY idx_trace_log_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
""".strip()


def _run_sql(sql: str, database: str = "") -> None:
    config = _log_db_config()
    mysql_cmd = os.getenv("CHATBI_MYSQL_CMD", "mysql")
    base_cmd = [
        mysql_cmd,
        f"-h{config['host']}",
        f"-P{config['port']}",
        f"-u{config['user']}",
        f"-p{config['password']}",
    ]
    tail_cmd = ["--default-character-set=utf8mb4"]
    if database:
        tail_cmd.append(database)
    tail_cmd.extend(["-e", sql])
    attempts = [["--ssl-mode=DISABLED"], ["--ssl=0"], []]
    for ssl_args in attempts:
        proc = subprocess.run(
            [*base_cmd, *ssl_args, *tail_cmd],
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )
        if proc.returncode == 0:
            return
        error = proc.stderr.strip()
        if "unknown variable" in error and ("ssl-mode" in error or "ssl=0" in error):
            continue
        if "TLS/SSL error" in error or "self-signed certificate" in error:
            continue
        return


def _payload_json(payload: Optional[Dict[str, Any]]) -> str:
    if payload is None:
        return "{}"
    text = json.dumps(payload, ensure_ascii=False, default=str)
    if len(text) <= MAX_PAYLOAD_LENGTH:
        return text
    return json.dumps({"truncated": True, "preview": text[:MAX_PAYLOAD_LENGTH]}, ensure_ascii=False)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")


def _quote(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "''") + "'"


def _safe_ident(value: str) -> str:
    if not value or "`" in value or "\x00" in value:
        return "chatbi_logs"
    return value
