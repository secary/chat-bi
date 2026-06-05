from __future__ import annotations

from typing import Any, Dict, List

from backend.agent.harness_business_flows_decision import (
    summarize_decision_content_audit_flow,
)
from backend.agent.harness_business_flows_llm import summarize_llm_config_flow
from backend.agent.harness_business_flows_semantic import summarize_semantic_query_flow

_UPLOAD_SKILLS = {"chatbi-file-ingestion", "chatbi-auto-analysis"}


def summarize_business_flows(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    flows: List[Dict[str, Any]] = []
    upload_flow = _summarize_upload_analysis_flow(events)
    if upload_flow:
        flows.append(upload_flow)
    semantic_query_flow = summarize_semantic_query_flow(events)
    if semantic_query_flow:
        flows.append(semantic_query_flow)
    decision_content_flow = summarize_decision_content_audit_flow(events)
    if decision_content_flow:
        flows.append(decision_content_flow)
    llm_config_flow = summarize_llm_config_flow(events)
    if llm_config_flow:
        flows.append(llm_config_flow)
    return flows


def _summarize_upload_analysis_flow(events: List[Dict[str, Any]]) -> Dict[str, Any] | None:
    upload_events = [event for event in events if _is_upload_related(event)]
    if not upload_events:
        return None

    file_events = [
        event for event in upload_events if _skill_name(event) == "chatbi-file-ingestion"
    ]
    auto_events = [event for event in upload_events if _skill_name(event) == "chatbi-auto-analysis"]

    file_success = _successful_observation(file_events)
    auto_success = _successful_observation(auto_events)
    file_failed = _failed(file_events)
    auto_failed = _failed(auto_events)

    analysis_mode = _first_text(file_events, "analysis_mode")
    row_count = _first_number(file_events, "row_count")
    auto_status = _first_text(auto_events, "status")
    has_dashboard = _any_bool(auto_events, "has_auto_analysis") or _any_bool(
        auto_events, "dashboard_ready"
    )

    steps = [
        {
            "key": "file_ingestion",
            "label": "文件读取",
            "status": _step_status(file_success, file_failed, bool(file_events)),
            "detail": _file_ingestion_detail(file_success, file_failed, row_count),
        },
        {
            "key": "schema_validation",
            "label": "结构校验",
            "status": _schema_status(file_success, analysis_mode),
            "detail": _schema_detail(file_success, analysis_mode),
        },
        {
            "key": "auto_analysis",
            "label": "自动分析",
            "status": _auto_status(file_success, auto_success, auto_failed, bool(auto_events)),
            "detail": _auto_detail(file_success, auto_success, auto_failed, auto_status),
        },
        {
            "key": "dashboard_generation",
            "label": "看板产出",
            "status": _dashboard_status(auto_success, auto_failed, has_dashboard),
            "detail": _dashboard_detail(auto_success, auto_failed, has_dashboard),
        },
    ]
    status = _flow_status(steps)
    return {
        "flow_key": "upload_analysis",
        "title": "上传分析链路",
        "status": status,
        "summary": _upload_summary(status, analysis_mode, has_dashboard, auto_status),
        "steps": steps,
    }


def _is_upload_related(event: Dict[str, Any]) -> bool:
    payload = event.get("payload") or {}
    skill = _skill_name(event)
    agent_id = str(payload.get("agent_id") or "")
    return skill in _UPLOAD_SKILLS or agent_id == "upload_analyst"


def _skill_name(event: Dict[str, Any]) -> str:
    payload = event.get("payload") or {}
    return str(payload.get("skill") or "").strip()


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


def _first_text(events: List[Dict[str, Any]], key: str) -> str:
    for event in reversed(events):
        payload = event.get("payload") or {}
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _first_number(events: List[Dict[str, Any]], key: str) -> int | None:
    for event in reversed(events):
        payload = event.get("payload") or {}
        value = payload.get(key)
        if isinstance(value, (int, float)):
            return int(value)
    return None


def _any_bool(events: List[Dict[str, Any]], key: str) -> bool:
    return any(bool((event.get("payload") or {}).get(key)) for event in events)


def _step_status(success: bool, failed: bool, started: bool) -> str:
    if failed:
        return "error"
    if success:
        return "completed"
    if started:
        return "warning"
    return "pending"


def _schema_status(file_success: bool, analysis_mode: str) -> str:
    if not file_success:
        return "pending"
    if analysis_mode == "schema_validated":
        return "completed"
    if analysis_mode == "profile_only":
        return "warning"
    return "completed"


def _auto_status(
    file_success: bool,
    auto_success: bool,
    auto_failed: bool,
    auto_started: bool,
) -> str:
    if auto_failed:
        return "error"
    if auto_success:
        return "completed"
    if auto_started:
        return "warning"
    if file_success:
        return "pending"
    return "pending"


def _dashboard_status(auto_success: bool, auto_failed: bool, has_dashboard: bool) -> str:
    if auto_failed:
        return "error"
    if has_dashboard:
        return "completed"
    if auto_success:
        return "pending"
    return "pending"


def _file_ingestion_detail(file_success: bool, file_failed: bool, row_count: int | None) -> str:
    if file_failed:
        return "文件读取或预处理失败。"
    if file_success and row_count is not None:
        return f"已读取上传文件，当前结果包含 {row_count} 行。"
    if file_success:
        return "已读取上传文件。"
    return "尚未看到文件读取结果。"


def _schema_detail(file_success: bool, analysis_mode: str) -> str:
    if not file_success:
        return "需先完成文件读取，才能判断是否匹配受控业务表。"
    if analysis_mode == "schema_validated":
        return "已匹配受控业务表，可继续执行上传数据分析。"
    if analysis_mode == "profile_only":
        return "未匹配受控业务表，当前按通用表结构继续分析。"
    return "已完成基础结构校验。"


def _auto_detail(
    file_success: bool,
    auto_success: bool,
    auto_failed: bool,
    auto_status: str,
) -> str:
    if auto_failed:
        return "自动分析执行失败。"
    if auto_success and auto_status == "need_confirmation":
        return "已生成指标提案，等待用户采纳或确认。"
    if auto_success:
        return "已生成上传数据分析结果。"
    if file_success:
        return "已具备 rows，可继续生成指标提案或执行分析。"
    return "尚未进入自动分析阶段。"


def _dashboard_detail(auto_success: bool, auto_failed: bool, has_dashboard: bool) -> str:
    if auto_failed:
        return "自动分析失败，未产出看板。"
    if has_dashboard:
        return "已生成前端可渲染的看板中间件。"
    if auto_success:
        return "自动分析已完成，但当前尚未检测到看板结果。"
    return "尚未产出看板。"


def _flow_status(steps: List[Dict[str, Any]]) -> str:
    statuses = [str(step.get("status") or "") for step in steps]
    if "error" in statuses:
        return "error"
    if "warning" in statuses:
        return "warning"
    if "completed" in statuses and all(status in {"completed", "pending"} for status in statuses):
        return "completed"
    return "pending"


def _upload_summary(status: str, analysis_mode: str, has_dashboard: bool, auto_status: str) -> str:
    if status == "error":
        return "上传分析链路存在失败节点，需要先恢复读取或自动分析。"
    if has_dashboard:
        return "上传分析链路已跑通，前端看板结果已就绪。"
    if auto_status == "need_confirmation":
        return "上传文件已完成读取，当前停在指标提案确认阶段。"
    if analysis_mode == "profile_only":
        return "上传文件已读取，但未命中受控业务表，当前按通用表分析。"
    if analysis_mode == "schema_validated":
        return "上传文件已完成结构校验，可继续自动分析或产出看板。"
    return "上传分析链路已被触发，当前可继续补齐后续分析步骤。"
