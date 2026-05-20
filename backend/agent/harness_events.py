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
) -> None:
    payload = {
        "skill": skill_name,
        "ok": ok,
        "result_kind": result_kind,
    }
    if error:
        payload["error"] = error
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
) -> None:
    _emit_harness_event(
        trace_id,
        state,
        "observation_built",
        extras={
            "action": "run_specialist",
            "round": round_index,
            "task_index": task_index,
            "agent_id": agent_id,
            "skill": last_skill_name or f"specialist:{agent_id}",
            "ok": ok,
            "observation_preview": observation[:240],
        },
    )


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
) -> None:
    payload = _payload(state, action)
    if extras:
        payload.update(extras)
    log_event(trace_id, "agent.harness", event_name, payload=payload)
