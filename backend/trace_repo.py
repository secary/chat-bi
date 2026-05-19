from __future__ import annotations

import json
from typing import Any, Dict, List

from backend.db_mysql import log_fetch_all
from backend.db_tables import TRACE_LOG


def list_trace_events(trace_id: str, limit: int = 500) -> List[Dict[str, Any]]:
    rows = log_fetch_all(
        f"SELECT id, trace_id, span_name, event_name, level, message, payload, created_at "
        f"FROM {TRACE_LOG} WHERE trace_id = %s ORDER BY id ASC LIMIT %s",
        (trace_id, limit),
    )
    return [_normalize_row(row) for row in rows]


def list_recent_trace_ids(limit: int = 20) -> List[Dict[str, Any]]:
    rows = log_fetch_all(
        f"SELECT trace_id, MAX(created_at) AS last_seen, COUNT(*) AS event_count "
        f"FROM {TRACE_LOG} GROUP BY trace_id ORDER BY last_seen DESC LIMIT %s",
        (limit,),
    )
    return [
        {
            "trace_id": str(row.get("trace_id") or ""),
            "last_seen": row.get("last_seen"),
            "event_count": int(row.get("event_count") or 0),
        }
        for row in rows
        if row.get("trace_id")
    ]


def _normalize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    payload = row.get("payload")
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            payload = None
    return {
        "id": int(row.get("id") or 0),
        "trace_id": str(row.get("trace_id") or ""),
        "span_name": str(row.get("span_name") or ""),
        "event_name": str(row.get("event_name") or ""),
        "level": str(row.get("level") or ""),
        "message": str(row.get("message") or ""),
        "payload": payload if isinstance(payload, dict) else {},
        "created_at": row.get("created_at"),
    }
