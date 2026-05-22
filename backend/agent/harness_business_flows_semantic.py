from __future__ import annotations

from typing import Any, Dict, List


def summarize_semantic_query_flow(events: List[Dict[str, Any]]) -> Dict[str, Any] | None:
    query_events = [event for event in events if _is_semantic_query_related(event)]
    if not query_events:
        return None

    query_success = _successful_observation(query_events)
    query_failed = _failed(query_events)
    plan_summary = _first_dict(query_events, "plan_summary")
    row_count = _first_number(query_events, "row_count")
    has_chart = _any_bool(query_events, "has_chart_plan")
    has_kpis = _first_number(query_events, "kpi_count")
    metric = str(plan_summary.get("metric") or "").strip() if plan_summary else ""
    dimensions = (
        [
            str(item).strip()
            for item in plan_summary.get("dimensions", []) or []
            if str(item).strip()
        ]
        if plan_summary
        else []
    )

    steps = [
        {
            "key": "semantic_match",
            "label": "语义命中",
            "status": _semantic_match_status(
                query_success, query_failed, bool(query_events), bool(plan_summary)
            ),
            "detail": _semantic_match_detail(query_success, query_failed, metric),
        },
        {
            "key": "query_plan",
            "label": "查询规划",
            "status": _query_plan_status(query_success, query_failed, bool(plan_summary)),
            "detail": _query_plan_detail(plan_summary, metric, dimensions),
        },
        {
            "key": "rows_ready",
            "label": "结果取回",
            "status": _rows_status(query_success, query_failed, row_count),
            "detail": _rows_detail(query_success, query_failed, row_count),
        },
        {
            "key": "visual_output",
            "label": "图表/KPI",
            "status": _visual_status(query_success, query_failed, has_chart, has_kpis),
            "detail": _visual_detail(query_success, query_failed, has_chart, has_kpis),
        },
    ]
    status = _flow_status(steps)
    return {
        "flow_key": "semantic_query",
        "title": "问数链路",
        "status": status,
        "summary": _query_summary(status, metric, row_count, has_chart, has_kpis),
        "steps": steps,
    }


def _is_semantic_query_related(event: Dict[str, Any]) -> bool:
    payload = event.get("payload") or {}
    return str(payload.get("skill") or "").strip() == "chatbi-semantic-query"


def _successful_observation(events: List[Dict[str, Any]]) -> bool:
    return any(
        event.get("span_name") == "agent.harness"
        and event.get("event_name") == "observation_built"
        and (event.get("payload") or {}).get("ok") is not False
        for event in events
    )


def _failed(events: List[Dict[str, Any]]) -> bool:
    return any(
        (event.get("span_name") == "agent.skill" and event.get("event_name") == "failed")
        or (
            event.get("span_name") == "agent.harness"
            and event.get("event_name") == "observation_built"
            and (event.get("payload") or {}).get("ok") is False
        )
        for event in events
    )


def _first_dict(events: List[Dict[str, Any]], key: str) -> Dict[str, Any]:
    for event in reversed(events):
        value = (event.get("payload") or {}).get(key)
        if isinstance(value, dict):
            return value
    return {}


def _first_number(events: List[Dict[str, Any]], key: str) -> int:
    for event in reversed(events):
        value = (event.get("payload") or {}).get(key)
        if isinstance(value, (int, float)):
            return int(value)
    return 0


def _any_bool(events: List[Dict[str, Any]], key: str) -> bool:
    return any(bool((event.get("payload") or {}).get(key)) for event in events)


def _semantic_match_status(success: bool, failed: bool, started: bool, has_plan: bool) -> str:
    if failed:
        return "error"
    if success and has_plan:
        return "completed"
    if started:
        return "warning"
    return "pending"


def _query_plan_status(success: bool, failed: bool, has_plan: bool) -> str:
    if failed:
        return "error"
    if has_plan:
        return "completed"
    if success:
        return "warning"
    return "pending"


def _rows_status(success: bool, failed: bool, row_count: int) -> str:
    if failed:
        return "error"
    if success and row_count > 0:
        return "completed"
    if success:
        return "warning"
    return "pending"


def _visual_status(success: bool, failed: bool, has_chart: bool, kpi_count: int) -> str:
    if failed:
        return "error"
    if has_chart or kpi_count > 0:
        return "completed"
    if success:
        return "pending"
    return "pending"


def _semantic_match_detail(success: bool, failed: bool, metric: str) -> str:
    if failed:
        return "问数执行失败，未形成稳定语义结果。"
    if success and metric:
        return f"已命中受控业务语义，当前核心指标为“{metric}”。"
    if success:
        return "已进入问数执行，但当前未记录清晰的语义规划摘要。"
    return "尚未进入演示库问数阶段。"


def _query_plan_detail(plan_summary: Dict[str, Any], metric: str, dimensions: List[str]) -> str:
    if not plan_summary:
        return "尚未看到明确的指标/维度规划结果。"
    parts: List[str] = []
    if metric:
        parts.append(f"指标：{metric}")
    if dimensions:
        parts.append(f"维度：{'、'.join(dimensions)}")
    return "；".join(parts) if parts else "已生成查询规划。"


def _rows_detail(success: bool, failed: bool, row_count: int) -> str:
    if failed:
        return "查询执行失败，未取回结果。"
    if success and row_count > 0:
        return f"已取回 {row_count} 条结果。"
    if success:
        return "查询已完成，但未返回数据。"
    return "尚未执行到结果取回阶段。"


def _visual_detail(success: bool, failed: bool, has_chart: bool, kpi_count: int) -> str:
    if failed:
        return "问数失败，未产出图表或 KPI。"
    if has_chart and kpi_count > 0:
        return "已生成图表规划，并同步产出 KPI 卡片。"
    if has_chart:
        return "已生成图表规划，可直接用于前端渲染。"
    if kpi_count > 0:
        return f"已生成 {kpi_count} 张 KPI 卡片。"
    if success:
        return "当前以表格结果为主，尚未检测到图表或 KPI。"
    return "尚未进入可视化产出阶段。"


def _flow_status(steps: List[Dict[str, Any]]) -> str:
    statuses = [str(step.get("status") or "") for step in steps]
    if "error" in statuses:
        return "error"
    if "warning" in statuses:
        return "warning"
    if "completed" in statuses and all(status in {"completed", "pending"} for status in statuses):
        return "completed"
    return "pending"


def _query_summary(
    status: str,
    metric: str,
    row_count: int,
    has_chart: bool,
    kpi_count: int,
) -> str:
    if status == "error":
        return "问数链路存在失败节点，需要先恢复语义解析或查询执行。"
    if has_chart or kpi_count > 0:
        return "问数链路已跑通，并已形成可直接展示的图表或 KPI。"
    if row_count > 0:
        return f"问数链路已返回 {row_count} 条结果，当前以表格结果为主。"
    if metric:
        return f"问数链路已识别指标“{metric}”，但当前还缺少稳定结果展示。"
    return "问数链路已被触发，当前可继续补齐规划或结果阶段。"
