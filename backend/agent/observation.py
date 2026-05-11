from __future__ import annotations

import json
from typing import Any, Dict


"""
turn skill result into a compact json string format for llm input.
"""


def summarize_observation(skill_name: str, result: Dict[str, Any]) -> str:
    """Compact JSON string for LLM context; avoids dumping full wide tables."""
    kind = result.get("kind", "")
    text = (result.get("text") or "")[:800]  #
    data = result.get("data")
    rows: list = []
    if isinstance(data, dict) and isinstance(data.get("rows"), list):
        rows = data["rows"]

    base: Dict[str, Any] = {
        "skill": skill_name,
        "ok": True,
        "kind": kind,
        "error": None,
    }

    if rows:
        cols = list(rows[0].keys()) if rows else []
        base["row_count"] = len(rows)
        base["columns"] = cols
        base["sample_rows"] = rows[:5]
    else:
        base["text_excerpt"] = text
        base["kpis"] = result.get("kpis") or []

    charts = result.get("charts") or []
    if charts:
        base["charts_count"] = len(charts)

    return json.dumps(base, ensure_ascii=False)
