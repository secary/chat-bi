"""User memory persistence (session summaries + long-term profile)."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from backend.db_mysql import app_connection, app_execute, app_fetch_all, app_fetch_one

_UPLOAD_PATH_RE = re.compile(r"/tmp/chatbi-uploads/[A-Za-z0-9._-]+", re.IGNORECASE)
_NOISE_MARKERS = (
    "请读取我上传的文件",
    "请读取我上传的图像",
    "按数据库表结构校验",
    "chatbi-file-ingestion",
    "基于这个文件",
    "这个文件里都有什么内容",
)


def _normalize_prompt(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _prompt_is_noise(text: str) -> bool:
    if not text:
        return True
    if len(text) > 48:
        return True
    if _UPLOAD_PATH_RE.search(text):
        return True
    return any(marker in text for marker in _NOISE_MARKERS)


def suggested_prompts_for_user(user_id: int, limit: int = 5) -> List[str]:
    try:
        rows = app_fetch_all(
            "SELECT title FROM user_memory "
            "WHERE user_id = %s AND kind = 'session_summary' "
            "AND title IS NOT NULL AND TRIM(title) <> '' "
            "ORDER BY updated_at DESC LIMIT %s",
            (user_id, limit),
        )
    except Exception:
        return []
    out: List[str] = []
    for row in rows:
        t = _normalize_prompt(str(row.get("title") or ""))
        if _prompt_is_noise(t):
            continue
        if t not in out:
            out.append(t)
        if len(out) >= limit:
            break
    return out


def insert_session_summary(
    user_id: int,
    session_id: int,
    title: str,
    content: str,
) -> int:
    with app_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM user_memory WHERE user_id = %s AND kind = 'session_summary' "
                "AND source_session_id = %s",
                (user_id, session_id),
            )
            cur.execute(
                "INSERT INTO user_memory (user_id, kind, title, content, source_session_id) "
                "VALUES (%s, 'session_summary', %s, %s, %s)",
                (user_id, title[:500], content, session_id),
            )
            return int(cur.lastrowid)


def list_recent_session_summaries(user_id: int, limit: int = 5) -> List[Dict[str, Any]]:
    return app_fetch_all(
        "SELECT id, title, content, source_session_id, updated_at "
        "FROM user_memory WHERE user_id = %s AND kind = 'session_summary' "
        "ORDER BY updated_at DESC LIMIT %s",
        (user_id, limit),
    )


def get_long_term_row(user_id: int) -> Optional[Dict[str, Any]]:
    return app_fetch_one(
        "SELECT id, content, updated_at FROM user_memory "
        "WHERE user_id = %s AND kind = 'long_term' LIMIT 1",
        (user_id,),
    )


def upsert_long_term(user_id: int, content: str) -> None:
    existing = get_long_term_row(user_id)
    if existing:
        app_execute(
            "UPDATE user_memory SET content = %s WHERE id = %s",
            (content, existing["id"]),
        )
        return
    app_execute(
        "INSERT INTO user_memory (user_id, kind, title, content) VALUES (%s, 'long_term', %s, %s)",
        (user_id, "用户习惯与偏好", content),
    )


def trim_session_summaries(user_id: int, keep: int = 30) -> None:
    rows = app_fetch_all(
        "SELECT id FROM user_memory WHERE user_id = %s AND kind = 'session_summary' "
        "ORDER BY updated_at DESC",
        (user_id,),
    )
    if len(rows) <= keep:
        return
    for row in rows[keep:]:
        app_execute("DELETE FROM user_memory WHERE id = %s", (int(row["id"]),))
