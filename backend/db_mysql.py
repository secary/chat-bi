"""Minimal MySQL helpers for app tables (chatbi_demo)."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Dict, Iterator, List, Optional

import pymysql
from pymysql.cursors import DictCursor

from backend.config import settings


@contextmanager
def app_connection() -> Iterator[pymysql.connections.Connection]:
    conn = pymysql.connect(
        host=settings.db_host,
        port=int(settings.db_port),
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_name,
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=True,
    )
    try:
        yield conn
    finally:
        conn.close()


def fetch_one(
    sql: str, args: Optional[tuple[Any, ...]] = None
) -> Optional[Dict[str, Any]]:
    with app_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, args or ())
            return cur.fetchone()


def fetch_all(sql: str, args: Optional[tuple[Any, ...]] = None) -> List[Dict[str, Any]]:
    with app_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, args or ())
            return list(cur.fetchall())


def execute(sql: str, args: Optional[tuple[Any, ...]] = None) -> int:
    with app_connection() as conn:
        with conn.cursor() as cur:
            return cur.execute(sql, args or ())


def test_mysql_connection(
    host: str,
    port: int,
    user: str,
    password: str,
    database: str,
) -> None:
    conn = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        charset="utf8mb4",
        cursorclass=DictCursor,
        connect_timeout=8,
    )
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 AS ok")
            row = cur.fetchone()
            if not row or row.get("ok") != 1:
                raise RuntimeError("unexpected SELECT 1 result")
    finally:
        conn.close()
