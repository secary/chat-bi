from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from backend.config import settings

MAX_PAYLOAD_LENGTH = 6000


def create_trace_table_sql() -> str:
    base = """
CREATE DATABASE IF NOT EXISTS `chatbi_logs`
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;
""".strip()
    db_ident = f"`{_safe_ident(settings.log_db_name)}`"
    return base.replace("`chatbi_logs`", db_ident)


def create_trace_log_table_sql() -> str:
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


def log_event(
    trace_id: str,
    span_name: str,
    event_name: str,
    message: str = "",
    payload: Optional[Dict[str, Any]] = None,
    level: str = "INFO",
) -> None:
    if not trace_id:
        return
    try:
        _run_sql(create_trace_table_sql())
        _run_sql(create_trace_log_table_sql(), database=settings.log_db_name)
        _run_sql(
            "INSERT INTO chatbi_trace_log "
            "(trace_id, span_name, event_name, level, message, payload, created_at) "
            f"VALUES ({_quote(trace_id)}, {_quote(span_name)}, {_quote(event_name)}, "
            f"{_quote(level)}, {_quote(message[:500])}, "
            f"CAST({_quote(_payload_json(payload))} AS JSON), {_quote(_now())});",
            database=settings.log_db_name,
        )
    except Exception:
        return


def _payload_json(payload: Optional[Dict[str, Any]]) -> str:
    if payload is None:
        return "{}"
    text = json.dumps(payload, ensure_ascii=False, default=str)
    if len(text) <= MAX_PAYLOAD_LENGTH:
        return text
    trimmed = text[:MAX_PAYLOAD_LENGTH]
    return json.dumps({"truncated": True, "preview": trimmed}, ensure_ascii=False)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")


def _run_sql(sql: str, database: str = "") -> None:
    config = settings.log_db_config
    base_cmd = [
        "mysql",
        f"-h{config['host']}",
        f"-P{config['port']}",
        f"-u{config['user']}",
        f"-p{config['password']}",
    ]
    tail_cmd = [
        "--default-character-set=utf8mb4",
    ]
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


def _quote(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "''") + "'"


def _safe_ident(value: str) -> str:
    if not value or "`" in value or "\x00" in value:
        return "chatbi_logs"
    return value
