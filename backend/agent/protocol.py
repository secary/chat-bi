from __future__ import annotations

from typing import Any, Dict, List


def normalize_skill_result(payload: Any, skill_name: str) -> Dict[str, Any]:
    if isinstance(payload, dict) and "kind" in payload:
        payload.setdefault("text", "")
        payload.setdefault("data", {})
        payload.setdefault("charts", [])
        payload.setdefault("kpis", [])
        return payload
    if isinstance(payload, list):
        return {
            "kind": "table",
            "text": table_summary(payload),
            "data": {"rows": payload},
            "charts": [],
            "kpis": [],
        }
    if isinstance(payload, dict) and "facts" in payload and "advices" in payload:
        return {"kind": "decision", "text": "", "data": payload, "charts": [], "kpis": []}
    return {"kind": "text", "text": f"「{skill_name}」执行完毕。", "data": payload}


def table_summary(rows: List[Dict[str, str]]) -> str:
    if not rows:
        return "查询完成，未返回数据。"
    if len(rows) == 1:
        parts = [f"{key}: {value}" for key, value in rows[0].items() if value]
        return f"查询完成：{'，'.join(parts)}"
    return f"查询完成，共返回 {len(rows)} 条结果。"
