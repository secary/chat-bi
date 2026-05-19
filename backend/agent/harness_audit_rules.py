from __future__ import annotations

from typing import Any, Dict, List


def evaluate_audit_rules(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
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
    if authorized == 0:
        issues.append(_issue("NO_AUTHORIZED_ACTION", "warning", "未发现 Harness 放行记录。"))
    if _repeated_executions(events):
        issues.append(_issue("REPEATED_SKILL", "warning", "检测到重复执行同一 skill。"))
    if not issues and executed == 0:
        issues.append(_issue("NO_SKILL_EXECUTION", "info", "本次请求未执行任何 skill。"))
    return issues


def _repeated_executions(events: List[Dict[str, Any]]) -> bool:
    seen: set[tuple[int, str]] = set()
    for event in events:
        if event["span_name"] != "agent.harness" or event["event_name"] != "action_executing":
            continue
        payload = event.get("payload") or {}
        key = (int(payload.get("step") or 0), str(payload.get("skill") or ""))
        if key in seen and key[1]:
            return True
        seen.add(key)
    return False


def _count(events: List[Dict[str, Any]], span_name: str, event_name: str) -> int:
    return sum(
        1
        for event in events
        if event["span_name"] == span_name and event["event_name"] == event_name
    )


def _issue(code: str, level: str, message: str) -> Dict[str, Any]:
    return {"code": code, "level": level, "message": message}
