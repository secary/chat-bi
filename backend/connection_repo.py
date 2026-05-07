"""app_db_connection CRUD + env mapping for Skill subprocess."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.config import settings
from backend.db_mysql import (
    admin_connection,
    admin_execute,
    admin_fetch_all,
    admin_fetch_one,
)


def skill_env_from_row(row: Dict[str, Any]) -> Dict[str, str]:
    return {
        "CHATBI_DB_HOST": str(row["host"]),
        "CHATBI_DB_PORT": str(int(row["port"])),
        "CHATBI_DB_USER": str(row["username"]),
        "CHATBI_DB_PASSWORD": str(row["password"]),
        "CHATBI_DB_NAME": str(row["database_name"]),
    }


def clear_other_defaults(except_id: Optional[int] = None) -> None:
    if except_id is None:
        admin_execute("UPDATE app_db_connection SET is_default = 0")
    else:
        admin_execute(
            "UPDATE app_db_connection SET is_default = 0 WHERE id <> %s",
            (except_id,),
        )


def list_connections() -> List[Dict[str, Any]]:
    return admin_fetch_all(
        "SELECT id, name, host, port, username, database_name, is_default, created_at "
        "FROM app_db_connection ORDER BY is_default DESC, id ASC"
    )


def get_connection(conn_id: int) -> Optional[Dict[str, Any]]:
    return admin_fetch_one(
        "SELECT id, name, host, port, username, password, database_name, is_default "
        "FROM app_db_connection WHERE id = %s",
        (conn_id,),
    )


def get_default_connection() -> Optional[Dict[str, Any]]:
    return admin_fetch_one(
        "SELECT id, name, host, port, username, password, database_name, is_default "
        "FROM app_db_connection WHERE is_default = 1 LIMIT 1"
    )


def resolve_skill_db_env(
    db_connection_id: Optional[int],
) -> Optional[Dict[str, str]]:
    """Return Skill subprocess DB env overrides, or None to use settings/env defaults."""
    row: Optional[Dict[str, Any]]
    if db_connection_id is not None:
        row = get_connection(db_connection_id)
        if row:
            return skill_env_from_row(row)
        return None
    row = get_default_connection()
    if row:
        return skill_env_from_row(row)
    return None


def effective_connection_view() -> Dict[str, Any]:
    """Active DB connection used by Skill scripts: default row first, then env."""
    row = get_default_connection()
    if row:
        return {
            "source": "saved_default",
            "id": row.get("id"),
            "name": row.get("name"),
            "host": row.get("host"),
            "port": int(row.get("port") or 3306),
            "username": row.get("username"),
            "database_name": row.get("database_name"),
            "is_default": bool(row.get("is_default")),
        }
    return {
        "source": "env",
        "id": None,
        "name": "环境变量默认连接",
        "host": settings.db_host,
        "port": int(settings.db_port),
        "username": settings.db_user,
        "database_name": settings.db_name,
        "is_default": False,
    }


def insert_connection(
    name: str,
    host: str,
    port: int,
    username: str,
    password: str,
    database_name: str,
    is_default: bool,
) -> int:
    if is_default:
        clear_other_defaults()
    with admin_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO app_db_connection "
                "(name, host, port, username, password, database_name, is_default) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (name, host, port, username, password, database_name, int(is_default)),
            )
            return int(cur.lastrowid)


def update_connection(
    conn_id: int,
    name: str,
    host: str,
    port: int,
    username: str,
    password: Optional[str],
    database_name: str,
    is_default: bool,
) -> None:
    if is_default:
        clear_other_defaults(except_id=conn_id)
    if password is None:
        admin_execute(
            "UPDATE app_db_connection SET name=%s, host=%s, port=%s, username=%s, "
            "database_name=%s, is_default=%s WHERE id=%s",
            (name, host, port, username, database_name, int(is_default), conn_id),
        )
    else:
        admin_execute(
            "UPDATE app_db_connection SET name=%s, host=%s, port=%s, username=%s, "
            "password=%s, database_name=%s, is_default=%s WHERE id=%s",
            (
                name,
                host,
                port,
                username,
                password,
                database_name,
                int(is_default),
                conn_id,
            ),
        )


def delete_connection(conn_id: int) -> None:
    admin_execute("DELETE FROM app_db_connection WHERE id = %s", (conn_id,))
