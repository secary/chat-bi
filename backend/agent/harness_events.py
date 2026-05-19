from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.agent.harness_schema import HarnessAction
from backend.agent.harness_state import HarnessState
from backend.trace import log_event


def log_harness_validated(trace_id: str, state: HarnessState, action: HarnessAction) -> None:
    log_event(
        trace_id,
        "agent.harness",
        "action_validated",
        payload=_payload(state, action),
    )


def log_harness_authorized(trace_id: str, state: HarnessState, action: HarnessAction) -> None:
    log_event(
        trace_id,
        "agent.harness",
        "action_authorized",
        payload=_payload(state, action),
    )


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
    payload = _payload(state, action)
    payload["args"] = args
    log_event(trace_id, "agent.harness", "action_executing", payload=payload)


def log_harness_observation(
    trace_id: str,
    state: HarnessState,
    *,
    skill_name: str,
    ok: bool,
    result_kind: str = "",
    error: str = "",
) -> None:
    payload = _payload(state, None)
    payload.update(
        {
            "skill": skill_name,
            "ok": ok,
            "result_kind": result_kind,
        }
    )
    if error:
        payload["error"] = error
    log_event(trace_id, "agent.harness", "observation_built", payload=payload)


def log_harness_finish(trace_id: str, state: HarnessState, action: HarnessAction) -> None:
    log_event(
        trace_id,
        "agent.harness",
        "finish_emitted",
        payload=_payload(state, action),
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
