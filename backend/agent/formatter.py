from __future__ import annotations

from typing import Any, AsyncGenerator, Dict, List

from backend.renderers.chart import plan_to_option
from backend.renderers.kpi import build_kpi_cards

"""
turn agent result into server event stream to show on the frontend page.
text, chart, charts, kpi_cards.

"""


"""
turn agent result into server event stream to show on the frontend page.
text, chart, charts, kpi_cards.

"""


"""
turn agent result into server event stream to show on the frontend page.
text, chart, charts, kpi_cards.

"""


async def stream_result_events(
    skill_name: str, plan: Dict[str, Any], result: Dict[str, Any]
) -> AsyncGenerator[Dict[str, Any], None]:
    data = result.get("data", {})
    plan_trace = data.get("plan_trace") if isinstance(data, dict) else None
    if isinstance(plan_trace, list):
        for item in plan_trace:
            text = str(item).strip()
            if text:
                yield {"type": "thinking", "content": text}

    plan_summary = data.get("plan_summary") if isinstance(data, dict) else None
    if not plan_trace and plan_summary:
        thinking = summarize_plan_summary(plan_summary)
        if thinking:
            yield {"type": "thinking", "content": thinking}

    visual_only = bool(result.get("charts")) or bool(result.get("kpis"))
    text = result.get("text") or ("" if visual_only else fallback_text(skill_name, result))
    if text:
        yield {"type": "text", "content": text}

    # if result has data.rows, use it to fill the chart and kpi graph.
    if plan_summary:
        yield {"type": "plan_summary", "content": plan_summary}
    analysis_proposal = data.get("analysis_proposal") if isinstance(data, dict) else None
    if isinstance(analysis_proposal, dict):
        yield {"type": "analysis_proposal", "content": analysis_proposal}
    dashboard_middleware = data.get("dashboard_middleware") if isinstance(data, dict) else None
    if isinstance(dashboard_middleware, dict):
        yield {"type": "dashboard_ready", "content": dashboard_middleware}
        return  # charts and kpis are bundled inside the dashboard card
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
    if kpi_config and _can_build_plan_kpis(rows):
        try:
            yield {"type": "kpi_cards", "content": build_kpi_cards(kpi_config, rows)}
        except Exception as exc:
            yield {"type": "thinking", "content": f"KPI 卡片生成跳过：{exc}"}


def table_rows(result: Dict[str, Any]) -> List[Dict[str, str]]:
    data = result.get("data", {})
    if isinstance(data, dict) and isinstance(data.get("rows"), list):
        return data["rows"]
    return []


def _can_build_plan_kpis(rows: List[Dict[str, str]]) -> bool:
    """
    Only allow finish-step KPI fallback for single-row summaries.
    Multi-row ranking/trend queries should not synthesize KPI cards from the
    first row, otherwise dimension values like "华东" can leak into the cards.
    """
    return len(rows) == 1


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


def summarize_plan_summary(plan_summary: Dict[str, Any]) -> str:
    metric = str(plan_summary.get("metric") or "").strip()
    dimensions = [
        str(item).strip() for item in plan_summary.get("dimensions", []) or [] if str(item).strip()
    ]
    filters = plan_summary.get("filters", []) or []
    time_filter = str(plan_summary.get("time_filter") or "").strip()
    parts: List[str] = []
    if metric:
        parts.append(f"指标={metric}")
    if dimensions:
        parts.append(f"维度={'、'.join(dimensions)}")
    if filters:
        rendered = []
        for item in filters:
            if not isinstance(item, dict):
                continue
            dim_name = str(item.get("dimension") or "").strip()
            value = str(item.get("value") or "").strip()
            if dim_name and value:
                rendered.append(f"{dim_name}={value}")
        if rendered:
            parts.append(f"过滤={'，'.join(rendered)}")
    if time_filter:
        parts.append(f"时间条件={time_filter}")
    if plan_summary.get("order_by_metric_desc") and metric:
        parts.append(f"排序=按{metric}降序")
    limit = plan_summary.get("limit")
    if limit is not None:
        parts.append(f"限制条数={limit}")
    if not parts:
        return ""
    return "查询计划：" + "；".join(parts)
