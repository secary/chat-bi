"""Read-only MySQL access to the effective business database (Skill subprocess target)."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Dict, Iterator, List, Optional

import pymysql
from pymysql.cursors import DictCursor

from backend.config import settings
from backend.connection_repo import resolve_skill_db_env

logger = logging.getLogger(__name__)


def _merged_connection_params() -> Dict[str, Any]:
    overrides = resolve_skill_db_env(None) or {}
    return {
        "host": str(overrides.get("CHATBI_DB_HOST", settings.db_host)),
        "port": int(overrides.get("CHATBI_DB_PORT", settings.db_port)),
        "user": str(overrides.get("CHATBI_DB_USER", settings.db_user)),
        "password": str(overrides.get("CHATBI_DB_PASSWORD", settings.db_password)),
        "database": str(overrides.get("CHATBI_DB_NAME", settings.db_name)),
    }


@contextmanager
def business_connection() -> Iterator[pymysql.connections.Connection]:
    p = _merged_connection_params()
    conn = pymysql.connect(
        host=p["host"],
        port=p["port"],
        user=p["user"],
        password=p["password"],
        database=p["database"],
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=True,
    )
    try:
        yield conn
    finally:
        conn.close()


def business_fetch_one(
    sql: str, args: Optional[tuple[Any, ...]] = None
) -> Optional[Dict[str, Any]]:
    with business_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, args or ())
            return cur.fetchone()


def business_fetch_all(
    sql: str, args: Optional[tuple[Any, ...]] = None
) -> List[Dict[str, Any]]:
    with business_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, args or ())
            return list(cur.fetchall())


def safe_table_count(table: str) -> int:
    """Return row count for table, or 0 if missing or error."""
    safe = "".join(c for c in table if c.isalnum() or c == "_")
    if safe != table or not safe:
        return 0
    try:
        row = business_fetch_one(f"SELECT COUNT(*) AS c FROM `{safe}`")
        if not row:
            return 0
        return int(row.get("c", 0))
    except Exception as exc:
        logger.warning("dashboard semantic count skipped for %s: %s", table, exc)
        return 0
