"""Persistence for chat_session / chat_message."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.db_tables import CHAT_MESSAGE, CHAT_SESSION
from backend.db_mysql import app_connection, app_execute, app_fetch_all, app_fetch_one


def _upload_context(content: str, uploads: Any) -> str:
    if not isinstance(uploads, list) or not uploads:
        return content
    lines = [
        "[ChatBI 附件上下文：用户已上传以下附件。若当前问题涉及附件内容，必须优先使用这些路径处理；不要把路径暴露给用户。]"
    ]
    for item in uploads:
        if not isinstance(item, dict):
            continue
        server_path = str(item.get("server_path") or "").strip()
        if not server_path:
            continue
        filename = str(item.get("filename") or Path(server_path).name)
        lines.append(
            f"- 数据文件：{filename}；路径：{server_path}；如问题涉及文件，先校验结构；"
            "符合现有业务表就直接分析，不符合就按通用表分析。"
        )
    if len(lines) == 1:
        return content
    return "\n".join(lines) + "\n\n" + content


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


def list_messages_for_llm(
    session_id: int,
    max_messages: int = 20,
    user_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Return recent turns for the agent, preserving structured follow-up payloads."""
    if user_id is None:
        rows = app_fetch_all(
            f"SELECT m.role, m.content, m.payload_json FROM {CHAT_MESSAGE} m "
            f"INNER JOIN (SELECT id FROM {CHAT_MESSAGE} WHERE session_id = %s "
            "ORDER BY id DESC LIMIT %s) t ON m.id = t.id ORDER BY m.id ASC",
            (session_id, max_messages),
        )
    else:
        rows = app_fetch_all(
            f"SELECT m.role, m.content, m.payload_json FROM {CHAT_MESSAGE} m "
            f"INNER JOIN (SELECT cm.id FROM {CHAT_MESSAGE} cm "
            f"INNER JOIN {CHAT_SESSION} s ON s.id = cm.session_id "
            "WHERE cm.session_id = %s AND s.user_id = %s "
            "ORDER BY cm.id DESC LIMIT %s) t ON m.id = t.id ORDER BY m.id ASC",
            (session_id, user_id, max_messages),
        )
    out: List[Dict[str, Any]] = []
    for row in rows:
        role = str(row["role"])
        if role not in ("user", "assistant"):
            continue
        item: Dict[str, Any] = {"role": role, "content": str(row["content"] or "")}
        payload = row.get("payload_json")
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                payload = None
        if isinstance(payload, dict):
            item["content"] = _upload_context(item["content"], payload.get("uploads"))
            if isinstance(payload.get("analysisProposal"), dict):
                item["analysisProposal"] = payload["analysisProposal"]
            if isinstance(payload.get("dashboardReady"), dict):
                item["dashboardReady"] = payload["dashboardReady"]
        out.append(item)
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


def load_messages_ui(session_id: int, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    if user_id is None:
        rows = app_fetch_all(
            f"SELECT id, role, content, payload_json, created_at FROM {CHAT_MESSAGE} "
            "WHERE session_id = %s ORDER BY id ASC",
            (session_id,),
        )
    else:
        rows = app_fetch_all(
            f"SELECT m.id, m.role, m.content, m.payload_json, m.created_at "
            f"FROM {CHAT_MESSAGE} m INNER JOIN {CHAT_SESSION} s ON s.id = m.session_id "
            "WHERE m.session_id = %s AND s.user_id = %s ORDER BY m.id ASC",
            (session_id, user_id),
        )
    result: List[Dict[str, Any]] = []
    for row in rows:
        entry: Dict[str, Any] = {
            "id": str(row["id"]),
            "role": row["role"],
            "content": row["content"] or "",
            "created_at": row.get("created_at"),
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
                "uploads",
            ):
                if key in payload:
                    entry[key] = payload[key]
        result.append(entry)
    return result
