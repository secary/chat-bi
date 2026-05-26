from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.agent.harness_schema import HarnessAction
from backend.agent.harness_state import HarnessState
from backend.trace import log_event


def log_harness_validated(trace_id: str, state: HarnessState, action: HarnessAction) -> None:
    _emit_harness_event(trace_id, state, "action_validated", action=action)


def log_harness_authorized(trace_id: str, state: HarnessState, action: HarnessAction) -> None:
    _emit_harness_event(trace_id, state, "action_authorized", action=action)


def log_harness_rejected(
    trace_id: str,
    state: HarnessState,
    *,
    category: str,
    reason: str,
    action: Optional[HarnessAction] = None,
) -> None:
    payload = _payload(state, action)
    payload["reason"] = reason
    payload["rejection_count"] = state.consecutive_rejections
    log_event(
        trace_id,
        "agent.harness",
        category,
        message=reason,
        payload=payload,
        level="WARN",
    )


def log_harness_executing(
    trace_id: str,
    state: HarnessState,
    action: HarnessAction,
    args: List[str],
) -> None:
    _emit_harness_event(
        trace_id,
        state,
        "action_executing",
        action=action,
        extras={"args": args},
    )


def log_harness_observation(
    trace_id: str,
    state: HarnessState,
    *,
    skill_name: str,
    ok: bool,
    result_kind: str = "",
    error: str = "",
    extras: Optional[Dict[str, Any]] = None,
) -> None:
    payload = {
        "skill": skill_name,
        "ok": ok,
        "result_kind": result_kind,
    }
    if error:
        payload["error"] = error
    if extras:
        payload.update(extras)
    _emit_harness_event(
        trace_id,
        state,
        "observation_built",
        extras=payload,
    )


def log_harness_finish(trace_id: str, state: HarnessState, action: HarnessAction) -> None:
    _emit_harness_event(
        trace_id,
        state,
        "finish_emitted",
        action=action,
    )


def log_harness_decision_content_audit(
    trace_id: str,
    state: HarnessState,
    *,
    skill_name: str,
    audit: Dict[str, Any],
    agent_id: str | None = None,
) -> None:
    issues = audit.get("issues") if isinstance(audit.get("issues"), list) else []
    audit_status = str(audit.get("status") or "ok")
    issue_count = int(audit.get("issue_count") or len(issues))
    payload: Dict[str, Any] = {
        "skill": skill_name,
        "audit_status": audit_status,
        "issue_count": issue_count,
        "issue_codes": [
            str(item.get("code") or "").strip()
            for item in issues
            if isinstance(item, dict) and str(item.get("code") or "").strip()
        ][:8],
        # Keep the full audit payload on the dedicated event so downstream
        # readers can migrate off observation_built without losing detail.
        "decision_content_audit": {
            "status": audit_status,
            "issue_count": issue_count,
            "issues": issues,
        },
    }
    if agent_id:
        payload["agent_id"] = agent_id
    level = "WARN" if payload["issue_count"] else "INFO"
    message = (
        f"决策建议内容审核发现 {payload['issue_count']} 个问题。"
        if payload["issue_count"]
        else "决策建议内容审核通过。"
    )
    _emit_harness_event(
        trace_id,
        state,
        "decision_content_audited",
        extras=payload,
        level=level,
        message=message,
    )


def log_harness_multi_batch_validated(
    trace_id: str,
    state: HarnessState,
    *,
    round_index: int,
    task_count: int,
    agent_ids: List[str],
) -> None:
    _emit_harness_event(
        trace_id,
        state,
        "action_validated",
        extras={
            "action": "delegate_tasks",
            "round": round_index,
            "task_count": task_count,
            "agent_ids": agent_ids,
        },
    )


def log_harness_multi_batch_authorized(
    trace_id: str,
    state: HarnessState,
    *,
    round_index: int,
    task_count: int,
    agent_ids: List[str],
) -> None:
    _emit_harness_event(
        trace_id,
        state,
        "action_authorized",
        extras={
            "action": "delegate_tasks",
            "round": round_index,
            "task_count": task_count,
            "agent_ids": agent_ids,
        },
    )


def log_harness_multi_task_executing(
    trace_id: str,
    state: HarnessState,
    *,
    round_index: int,
    task_index: int,
    agent_id: str,
    handoff_instruction: str,
    depends_on: Optional[int],
) -> None:
    extras: Dict[str, Any] = {
        "action": "run_specialist",
        "round": round_index,
        "task_index": task_index,
        "agent_id": agent_id,
        "skill": f"specialist:{agent_id}",
        "handoff_preview": handoff_instruction[:160],
    }
    if depends_on is not None:
        extras["depends_on"] = depends_on
    _emit_harness_event(trace_id, state, "action_executing", extras=extras)


def log_harness_multi_task_observation(
    trace_id: str,
    state: HarnessState,
    *,
    round_index: int,
    task_index: int,
    agent_id: str,
    observation: str,
    last_skill_name: Optional[str],
    ok: bool = True,
    result_kind: str = "",
    has_result: bool = False,
    has_rows: bool = False,
    has_auto_analysis: bool = False,
    dependency_warning: str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    payload: Dict[str, Any] = {
        "action": "run_specialist",
        "round": round_index,
        "task_index": task_index,
        "agent_id": agent_id,
        "skill": last_skill_name or f"specialist:{agent_id}",
        "ok": ok,
        "observation_preview": observation[:240],
        "has_result": has_result,
        "has_rows": has_rows,
        "has_auto_analysis": has_auto_analysis,
    }
    if result_kind:
        payload["result_kind"] = result_kind
    if dependency_warning:
        payload["dependency_warning"] = dependency_warning[:200]
    if metadata:
        payload.update(metadata)
    _emit_harness_event(trace_id, state, "observation_built", extras=payload)


def log_harness_multi_finish(
    trace_id: str,
    state: HarnessState,
    *,
    block_count: int,
    round_count: int,
) -> None:
    _emit_harness_event(
        trace_id,
        state,
        "finish_emitted",
        extras={
            "action": "finish",
            "block_count": block_count,
            "round_count": round_count,
        },
    )


def log_harness_multi_summary_dependency_unmet(
    trace_id: str,
    state: HarnessState,
    *,
    warnings: List[str],
) -> None:
    _emit_harness_event(
        trace_id,
        state,
        "summary_dependency_unmet",
        extras={
            "action": "finish",
            "warning_count": len(warnings),
            "warnings": warnings[:3],
        },
    )


def _payload(state: HarnessState, action: Optional[HarnessAction]) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "mode": state.mode,
        "step": state.step_index,
        "max_steps": state.max_steps,
        "completed_skills": state.completed_skills[-6:],
        "last_skill_name": state.last_skill_name,
        "rejection_count": state.consecutive_rejections,
    }
    if action is not None:
        payload["action"] = action.action
        if action.skill:
            payload["skill"] = action.skill
        if action.text:
            payload["text_preview"] = action.text[:160]
        if action.thought:
            payload["thought_preview"] = action.thought[:160]
    return payload


def _emit_harness_event(
    trace_id: str,
    state: HarnessState,
    event_name: str,
    *,
    action: Optional[HarnessAction] = None,
    extras: Optional[Dict[str, Any]] = None,
    level: str = "INFO",
    message: str = "",
) -> None:
    payload = _payload(state, action)
    if extras:
        payload.update(extras)
    log_event(trace_id, "agent.harness", event_name, message=message, payload=payload, level=level)
