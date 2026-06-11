from __future__ import annotations

from typing import Any, Dict, List


def evaluate_audit_rules(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    agent_events_present = any(
        str(event.get("span_name") or "").startswith("agent.") for event in events
    )
    schema_rejects = _count(events, "agent.harness", "schema_rejected")
    policy_rejects = _count(events, "agent.harness", "policy_rejected")
    skill_failed = _count(events, "agent.skill", "failed")
    exhausted = any(
        event["span_name"] == "agent.runner"
        and event["event_name"] == "completed"
        and bool((event.get("payload") or {}).get("exhausted"))
        for event in events
    )
    authorized = _count(events, "agent.harness", "action_authorized")
    executed = _count(events, "agent.harness", "action_executing")
    observations = _count(events, "agent.harness", "observation_built")
    finishes = _count(events, "agent.harness", "finish_emitted")
    empty_legacy_specialist_outcomes = _empty_legacy_specialist_outcomes(events)
    dependency_warnings = _dependency_warnings(events)
    summary_dependency_unmet = _summary_dependency_unmet(events)
    decision_content_issues = _decision_content_issues(events)
    llm_config_failure = _llm_config_failure(events)

    if schema_rejects:
        issues.append(
            _issue(
                "HARNESS_SCHEMA_REJECTED",
                "warning" if schema_rejects < 3 else "error",
                f"Harness schema 拒绝了 {schema_rejects} 次动作。",
            )
        )
    if policy_rejects:
        issues.append(
            _issue(
                "HARNESS_POLICY_REJECTED",
                "warning" if policy_rejects < 3 else "error",
                f"Harness policy 拒绝了 {policy_rejects} 次动作。",
            )
        )
    if skill_failed:
        issues.append(_issue("SKILL_FAILED", "error", f"共有 {skill_failed} 次 skill 执行失败。"))
    if exhausted:
        issues.append(_issue("STEP_EXHAUSTED", "error", "请求达到最大推理步数后才结束。"))
    if executed and not observations:
        issues.append(
            _issue("MISSING_OBSERVATION", "error", "存在工具执行，但未记录 observation。")
        )
    if executed and not finishes:
        issues.append(
            _issue("MISSING_FINISH_EVENT", "warning", "存在执行记录，但未看到 finish 事件。")
        )
    if empty_legacy_specialist_outcomes:
        issues.append(
            _issue(
                "EMPTY_LEGACY_SPECIALIST_OUTCOME",
                "warning",
                f"有 {empty_legacy_specialist_outcomes} 个历史 specialist 事件未产出有效结果。",
            )
        )
    if dependency_warnings:
        issues.append(
            _issue(
                "DOWNSTREAM_DATA_MISSING",
                "warning",
                f"检测到下游依赖未满足：{dependency_warnings[0]}",
            )
        )
    if summary_dependency_unmet:
        issues.append(
            _issue(
                "SUMMARY_WITH_UNMET_DEPENDENCY",
                "warning",
                "历史汇总事件显示依赖未满足时仍进入了汇总阶段。",
            )
        )
    if llm_config_failure:
        issues.append(
            _issue(
                "LLM_CONFIG_TEST_FAILED",
                "error",
                llm_config_failure,
            )
        )
    issues.extend(decision_content_issues)
    if agent_events_present and authorized == 0:
        issues.append(_issue("NO_AUTHORIZED_ACTION", "warning", "未发现 Harness 放行记录。"))
    if _repeated_executions(events):
        issues.append(_issue("REPEATED_SKILL", "warning", "检测到重复执行同一 skill。"))
    if agent_events_present and not issues and executed == 0:
        issues.append(_issue("NO_SKILL_EXECUTION", "info", "本次请求未执行任何 skill。"))
    return issues


def _repeated_executions(events: List[Dict[str, Any]]) -> bool:
    seen: set[tuple[int, str]] = set()
    for event in events:
        if event["span_name"] != "agent.harness" or event["event_name"] != "action_executing":
            continue
        payload = event.get("payload") or {}
        key = (
            int(payload.get("step") or 0),
            int(payload.get("task_index") or -1),
            str(payload.get("skill") or ""),
        )
        if key in seen and key[2]:
            return True
        seen.add(key)
    return False


def _count(events: List[Dict[str, Any]], span_name: str, event_name: str) -> int:
    return sum(
        1
        for event in events
        if event["span_name"] == span_name and event["event_name"] == event_name
    )


def _empty_legacy_specialist_outcomes(events: List[Dict[str, Any]]) -> int:
    count = 0
    for event in events:
        if event["span_name"] != "agent.harness" or event["event_name"] != "observation_built":
            continue
        payload = event.get("payload") or {}
        if payload.get("action") != "run_specialist":
            continue
        if payload.get("ok") is False:
            continue
        if bool(payload.get("has_result")):
            continue
        count += 1
    return count


def _dependency_warnings(events: List[Dict[str, Any]]) -> List[str]:
    warnings: List[str] = []
    for event in events:
        if event["span_name"] != "agent.harness" or event["event_name"] != "observation_built":
            continue
        payload = event.get("payload") or {}
        warning = str(payload.get("dependency_warning") or "").strip()
        if warning:
            warnings.append(warning)
    return warnings


def _summary_dependency_unmet(events: List[Dict[str, Any]]) -> bool:
    return any(
        event["span_name"] == "agent.harness" and event["event_name"] == "summary_dependency_unmet"
        for event in events
    )


def _issue(code: str, level: str, message: str) -> Dict[str, Any]:
    return {"code": code, "level": level, "message": message}


def _decision_content_issues(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    found: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for event in events:
        if event["span_name"] != "agent.harness" or event["event_name"] != "observation_built":
            continue
        payload = event.get("payload") or {}
        audit = payload.get("decision_content_audit")
        if not isinstance(audit, dict):
            continue
        for item in audit.get("issues") or []:
            if not isinstance(item, dict):
                continue
            code = str(item.get("code") or "").strip()
            message = str(item.get("message") or "").strip()
            if not code or code in seen:
                continue
            seen.add(code)
            found.append(
                _issue(
                    code,
                    str(item.get("level") or "warning"),
                    message or "决策建议内容审核发现风险。",
                )
            )
    return found


def _llm_config_failure(events: List[Dict[str, Any]]) -> str:
    for event in reversed(events):
        if event["span_name"] != "admin.llm_settings":
            continue
        if event["event_name"] not in {"profile_probe_tested", "profile_tested"}:
            continue
        payload = event.get("payload") or {}
        if payload.get("ok") is not False:
            continue
        message = str(payload.get("message") or "").strip()
        if message:
            return f"LLM 配置测试失败：{message}"
        return "LLM 配置测试失败，请检查模型名、Base URL 和 API Key。"
    return ""
