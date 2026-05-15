"""Persistence for chat_session / chat_message."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from backend.db_tables import CHAT_MESSAGE, CHAT_SESSION
from backend.db_mysql import app_connection, app_execute, app_fetch_all, app_fetch_one


def create_session(user_id: int, title: str = "新对话") -> int:
    with app_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"INSERT INTO {CHAT_SESSION} (title, user_id) VALUES (%s, %s)",
                (title, user_id),
            )
            return int(cur.lastrowid)


def list_sessions(user_id: int, limit: int = 100) -> List[Dict[str, Any]]:
    return app_fetch_all(
        f"SELECT id, title, created_at, updated_at FROM {CHAT_SESSION} "
        "WHERE user_id = %s ORDER BY updated_at DESC LIMIT %s",
        (user_id, limit),
    )


def get_session_for_user(session_id: int, user_id: int) -> Optional[Dict[str, Any]]:
    return app_fetch_one(
        f"SELECT id, title, created_at, updated_at, user_id FROM {CHAT_SESSION} "
        "WHERE id = %s AND user_id = %s",
        (session_id, user_id),
    )


def update_session_title(session_id: int, user_id: int, title: str) -> None:
    app_execute(
        f"UPDATE {CHAT_SESSION} SET title = %s WHERE id = %s AND user_id = %s",
        (title, session_id, user_id),
    )


def touch_session(session_id: int, user_id: int) -> None:
    app_execute(
        f"UPDATE {CHAT_SESSION} SET updated_at = CURRENT_TIMESTAMP(6) WHERE id = %s AND user_id = %s",
        (session_id, user_id),
    )


def delete_session(session_id: int, user_id: int) -> None:
    app_execute(
        f"DELETE FROM {CHAT_SESSION} WHERE id = %s AND user_id = %s",
        (session_id, user_id),
    )


def list_messages_for_llm(session_id: int, max_messages: int = 20) -> List[Dict[str, str]]:
    """Return recent turns as role/content pairs for LLM (text only, chronological)."""
    rows = app_fetch_all(
        f"SELECT m.role, m.content FROM {CHAT_MESSAGE} m "
        f"INNER JOIN (SELECT id FROM {CHAT_MESSAGE} WHERE session_id = %s "
        "ORDER BY id DESC LIMIT %s) t ON m.id = t.id ORDER BY m.id ASC",
        (session_id, max_messages),
    )
    out: List[Dict[str, str]] = []
    for row in rows:
        role = str(row["role"])
        if role not in ("user", "assistant"):
            continue
        out.append({"role": role, "content": str(row["content"] or "")})
    return out


def insert_message(
    session_id: int,
    role: str,
    content: str,
    payload: Optional[Dict[str, Any]] = None,
) -> int:
    with app_connection() as conn:
        with conn.cursor() as cur:
            if payload is None:
                cur.execute(
                    f"INSERT INTO {CHAT_MESSAGE} (session_id, role, content, payload_json) "
                    "VALUES (%s, %s, %s, NULL)",
                    (session_id, role, content),
                )
            else:
                payload_json = json.dumps(payload, ensure_ascii=False)
                cur.execute(
                    f"INSERT INTO {CHAT_MESSAGE} (session_id, role, content, payload_json) "
                    "VALUES (%s, %s, %s, CAST(%s AS JSON))",
                    (session_id, role, content, payload_json),
                )
            return int(cur.lastrowid)


def load_messages_ui(session_id: int) -> List[Dict[str, Any]]:
    rows = app_fetch_all(
        f"SELECT id, role, content, payload_json FROM {CHAT_MESSAGE} "
        "WHERE session_id = %s ORDER BY id ASC",
        (session_id,),
    )
    result: List[Dict[str, Any]] = []
    for row in rows:
        entry: Dict[str, Any] = {
            "id": str(row["id"]),
            "role": row["role"],
            "content": row["content"] or "",
        }
        payload = row.get("payload_json")
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                payload = None
        if isinstance(payload, dict):
            for key in (
                "thinking",
                "chart",
                "kpiCards",
                "planSummary",
                "analysisProposal",
                "dashboardReady",
                "error",
            ):
                if key in payload:
                    entry[key] = payload[key]
        result.append(entry)
    return result
