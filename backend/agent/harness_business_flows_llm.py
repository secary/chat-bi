from __future__ import annotations

from typing import Any, Dict, List

_LLM_EVENTS = {
    "viewed",
    "profile_probe_tested",
    "profile_created",
    "profile_updated",
    "profile_tested",
    "active_profile_set",
}


def summarize_llm_config_flow(events: List[Dict[str, Any]]) -> Dict[str, Any] | None:
    llm_events = [event for event in events if _is_llm_config_event(event)]
    if not llm_events:
        return None

    viewed = _has_event(llm_events, "viewed")
    probe_success = _has_ok(llm_events, "profile_probe_tested")
    test_success = _has_ok(llm_events, "profile_tested")
    probe_failed = _has_failed(llm_events, "profile_probe_tested")
    test_failed = _has_failed(llm_events, "profile_tested")
    saved = _has_event(llm_events, "profile_created") or _has_event(llm_events, "profile_updated")
    activated = _has_event(llm_events, "active_profile_set")
    failure_detail = _failure_detail(llm_events)

    steps = [
        {
            "key": "open_settings",
            "label": "打开配置",
            "status": "completed" if viewed else "pending",
            "detail": "已进入 LLM 配置页。" if viewed else "未看到配置页读取记录。",
        },
        {
            "key": "connection_probe",
            "label": "测试连接",
            "status": _test_status(probe_success or test_success, probe_failed or test_failed),
            "detail": _test_detail(
                probe_success or test_success, probe_failed or test_failed, failure_detail
            ),
        },
        {
            "key": "profile_saved",
            "label": "保存配置",
            "status": "completed" if saved else "pending",
            "detail": "模型配置已写入已保存模型。" if saved else "未看到新增或更新模型配置记录。",
        },
        {
            "key": "profile_activated",
            "label": "启用配置",
            "status": "completed" if activated else "pending",
            "detail": "已切换当前使用配置。" if activated else "未看到启用配置记录。",
        },
    ]
    status = _flow_status(steps)
    return {
        "flow_key": "llm_config",
        "title": "LLM 配置链路",
        "status": status,
        "summary": _summary(status, failure_detail),
        "steps": steps,
    }


def _is_llm_config_event(event: Dict[str, Any]) -> bool:
    return (
        event.get("span_name") == "admin.llm_settings"
        and str(event.get("event_name") or "") in _LLM_EVENTS
    )


def _has_event(events: List[Dict[str, Any]], event_name: str) -> bool:
    return any(event.get("event_name") == event_name for event in events)


def _has_ok(events: List[Dict[str, Any]], event_name: str) -> bool:
    return any(
        event.get("event_name") == event_name and (event.get("payload") or {}).get("ok") is True
        for event in events
    )


def _has_failed(events: List[Dict[str, Any]], event_name: str) -> bool:
    return any(
        event.get("event_name") == event_name and (event.get("payload") or {}).get("ok") is False
        for event in events
    )


def _failure_detail(events: List[Dict[str, Any]]) -> str:
    for event in reversed(events):
        if event.get("event_name") not in {"profile_probe_tested", "profile_tested"}:
            continue
        payload = event.get("payload") or {}
        if payload.get("ok") is not False:
            continue
        message = str(payload.get("message") or "").strip()
        if message:
            return message
    return ""


def _test_status(success: bool, failed: bool) -> str:
    if failed:
        return "error"
    if success:
        return "completed"
    return "pending"


def _test_detail(success: bool, failed: bool, failure_detail: str) -> str:
    if failed:
        return failure_detail or "连接测试失败，请检查模型名、Base URL 和 API Key。"
    if success:
        return "连接测试通过。"
    return "尚未看到连接测试记录。"


def _flow_status(steps: List[Dict[str, Any]]) -> str:
    statuses = {step["status"] for step in steps}
    if "error" in statuses:
        return "error"
    if "pending" in statuses:
        return "warning"
    return "completed"


def _summary(status: str, failure_detail: str) -> str:
    if status == "error":
        return failure_detail or "LLM 配置流程未通过连接测试。"
    if status == "warning":
        return "LLM 配置流程尚未完整完成。"
    return "LLM 配置已测试、保存并启用。"
