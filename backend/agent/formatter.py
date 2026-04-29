from __future__ import annotations

from typing import Any, AsyncGenerator, Dict, List

from backend.renderers.chart import plan_to_option
from backend.renderers.kpi import build_kpi_cards


async def stream_result_events(
    skill_name: str, plan: Dict[str, Any], result: Dict[str, Any]
) -> AsyncGenerator[Dict[str, Any], None]:
    text = result.get("text") or fallback_text(skill_name, result)
    if text:
        yield {"type": "text", "content": text}

    rows = table_rows(result)
    chart_plan = plan.get("chart_plan")
    if chart_plan and rows:
        try:
            yield {"type": "chart", "content": plan_to_option(chart_plan, rows)}
        except Exception as exc:
            yield {"type": "thinking", "content": f"图表生成跳过：{exc}"}

    for chart in result.get("charts", []) or []:
        yield {"type": "chart", "content": chart}

    kpis = result.get("kpis", []) or []
    if kpis:
        yield {"type": "kpi_cards", "content": kpis}
        return

    kpi_config = plan.get("kpi_cards")
    if kpi_config and rows:
        try:
            yield {"type": "kpi_cards", "content": build_kpi_cards(kpi_config, rows)}
        except Exception as exc:
            yield {"type": "thinking", "content": f"KPI 卡片生成跳过：{exc}"}


def table_rows(result: Dict[str, Any]) -> List[Dict[str, str]]:
    data = result.get("data", {})
    if isinstance(data, dict) and isinstance(data.get("rows"), list):
        return data["rows"]
    return []


def fallback_text(skill_name: str, result: Dict[str, Any]) -> str:
    kind = result.get("kind", "text")
    if kind == "table":
        return summarize_rows(table_rows(result))
    return f"「{skill_name}」执行完毕。"


def summarize_rows(rows: List[Dict[str, str]]) -> str:
    if not rows:
        return "查询完成，未返回数据。"
    if len(rows) == 1:
        parts = [f"{key}: {value}" for key, value in rows[0].items() if value]
        return f"查询完成：{'，'.join(parts)}"
    return f"查询完成，共返回 {len(rows)} 条结果。"
