"""Application users (app_user)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from backend.db_mysql import app_connection, app_execute, app_fetch_all, app_fetch_one


def get_by_username(username: str) -> Optional[Dict[str, Any]]:
    return app_fetch_one(
        "SELECT id, username, password_hash, role, is_active, created_at "
        "FROM app_user WHERE username = %s",
        (username,),
    )


def get_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    return app_fetch_one(
        "SELECT id, username, password_hash, role, is_active, created_at "
        "FROM app_user WHERE id = %s",
        (user_id,),
    )


def list_users() -> List[Dict[str, Any]]:
    return app_fetch_all(
        "SELECT id, username, role, is_active, created_at FROM app_user ORDER BY id ASC"
    )


def create_user(username: str, password_hash: str, role: str) -> int:
    with app_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO app_user (username, password_hash, role) VALUES (%s, %s, %s)",
                (username, password_hash, role),
            )
            return int(cur.lastrowid)


def update_user(
    user_id: int,
    *,
    password_hash: Optional[str] = None,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> None:
    parts: List[str] = []
    args: List[Any] = []
    if password_hash is not None:
        parts.append("password_hash = %s")
        args.append(password_hash)
    if role is not None:
        parts.append("role = %s")
        args.append(role)
    if is_active is not None:
        parts.append("is_active = %s")
        args.append(int(is_active))
    if not parts:
        return
    args.append(user_id)
    app_execute(f"UPDATE app_user SET {', '.join(parts)} WHERE id = %s", tuple(args))


def delete_user(user_id: int) -> None:
    app_execute("DELETE FROM app_user WHERE id = %s", (user_id,))
