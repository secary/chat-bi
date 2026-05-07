"""Minimal MySQL helpers for app/user tables and admin/config tables."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Dict, Iterator, List, Optional

import pymysql
from pymysql.cursors import DictCursor

from backend.config import settings


def target_db_config(target: str) -> Dict[str, str]:
    if target == "admin":
        return settings.admin_db_config
    return settings.app_db_config


@contextmanager
def _connection_for(target: str) -> Iterator[pymysql.connections.Connection]:
    cfg = target_db_config(target)
    conn = pymysql.connect(
        host=cfg["host"],
        port=int(cfg["port"]),
        user=cfg["user"],
        password=cfg["password"],
        database=cfg["database"],
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=True,
    )
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def app_connection() -> Iterator[pymysql.connections.Connection]:
    with _connection_for("app") as conn:
        yield conn


@contextmanager
def admin_connection() -> Iterator[pymysql.connections.Connection]:
    with _connection_for("admin") as conn:
        yield conn


def app_fetch_one(
    sql: str, args: Optional[tuple[Any, ...]] = None
) -> Optional[Dict[str, Any]]:
    with app_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, args or ())
            return cur.fetchone()


def app_fetch_all(
    sql: str, args: Optional[tuple[Any, ...]] = None
) -> List[Dict[str, Any]]:
    with app_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, args or ())
            return list(cur.fetchall())


def app_execute(sql: str, args: Optional[tuple[Any, ...]] = None) -> int:
    with app_connection() as conn:
        with conn.cursor() as cur:
            return cur.execute(sql, args or ())


def admin_fetch_one(
    sql: str, args: Optional[tuple[Any, ...]] = None
) -> Optional[Dict[str, Any]]:
    with admin_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, args or ())
            return cur.fetchone()


def admin_fetch_all(
    sql: str, args: Optional[tuple[Any, ...]] = None
) -> List[Dict[str, Any]]:
    with admin_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, args or ())
            return list(cur.fetchall())


def admin_execute(sql: str, args: Optional[tuple[Any, ...]] = None) -> int:
    with admin_connection() as conn:
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
