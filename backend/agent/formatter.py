from __future__ import annotations

from typing import Any, AsyncGenerator, Dict, List

from backend.renderers.chart import plan_to_option
from backend.renderers.kpi import build_kpi_cards


"""
turn agent result into server event stream to show on the frontend page. 
text, chart, charts, kpi_cards.

"""
async def stream_result_events(
    skill_name: str, plan: Dict[str, Any], result: Dict[str, Any]
) -> AsyncGenerator[Dict[str, Any], None]:
    visual_only = bool(result.get("charts")) or bool(result.get("kpis"))
    text = result.get("text") or ("" if visual_only else fallback_text(skill_name, result))
    if text:
        yield {"type": "text", "content": text}

    # if result has data.rows, use it to fill the chart and kpi graph. 
    rows = table_rows(result)
    chart_plan = result.get("chart_plan") or plan.get("chart_plan")
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

"""
if result no chart or kpi graph, then return text. 
"""
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
