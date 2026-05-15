from __future__ import annotations

import json
import re
from typing import Any, Dict

# Compact observation summaries for agent tool results (fed back into agent prompts).

_WHERE_SPLIT = re.compile(r"\bWHERE\b", re.IGNORECASE)
_GROUP_ORDER_LIMIT = re.compile(r"\b(GROUP\s+BY|ORDER\s+BY|LIMIT)\b", re.IGNORECASE)
_EQ_COL_PATTERN = re.compile(r"^`([^`]+)`\s*=\s*")


def _where_clause_excerpt(sql: str) -> str:
    m = _WHERE_SPLIT.search(sql)
    if not m:
        return ""
    tail = sql[m.end() :].strip()
    cut = _GROUP_ORDER_LIMIT.search(tail)
    if cut:
        return tail[: cut.start()].strip()
    return tail


def _where_has_repeated_equality_on_same_column(where_sql: str) -> bool:
    """Heuristic: multiple ``col =`` on the same column (not IN) often contradict."""
    if not where_sql.strip():
        return False
    parts = [p.strip() for p in where_sql.split(" AND ")]
    seen_eq: set[str] = set()
    for part in parts:
        if " IN (" in part.upper():
            continue
        em = _EQ_COL_PATTERN.match(part)
        if not em:
            continue
        col = em.group(1)
        if col in seen_eq:
            return True
        seen_eq.add(col)
    return False


def summarize_observation(skill_name: str, result: Dict[str, Any]) -> str:
    """Compact JSON string for LLM context; avoids dumping full wide tables."""
    kind = result.get("kind", "")
    text = (result.get("text") or "")[:800]
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

    if isinstance(data, dict) and isinstance(data.get("rows"), list):
        base["row_count"] = len(rows)

    if rows:
        cols = list(rows[0].keys()) if rows else []
        base["columns"] = cols
        base["sample_rows"] = rows[:5]
    if skill_name == "chatbi-comparison" and isinstance(data, dict):
        meta = data.get("comparison_meta")
        if isinstance(meta, dict):
            base["comparison_period"] = {
                "year": meta.get("year"),
                "cur_month": meta.get("cur_month"),
                "prev_month": meta.get("prev_month"),
            }
    if not rows:
        base["text_excerpt"] = text
        base["kpis"] = result.get("kpis") or []
        if skill_name == "chatbi-semantic-query" and isinstance(data, dict) and not rows:
            sql = str(data.get("sql") or "")
            if sql:
                base["sql_excerpt"] = sql[:800]
            where_ex = _where_clause_excerpt(sql)
            if where_ex and _where_has_repeated_equality_on_same_column(where_ex):
                base["empty_result_hint"] = (
                    "WHERE 中对同一列出现多个「=」等值条件时通常互斥，查询恒为空；"
                    "应改为 IN 或单一条件。若由 Manager 交办枚举维度值引起，可仅用用户原述重试问数。"
                )

    charts = result.get("charts") or []
    if charts:
        base["charts_count"] = len(charts)

    return json.dumps(base, ensure_ascii=False)
