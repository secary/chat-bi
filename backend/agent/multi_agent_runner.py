"""Multi-agent orchestration: Manager plan → specialists (subtasks) → synthesis."""

from __future__ import annotations

from typing import Any, AsyncGenerator, Dict, List, Optional

from backend.agent.multi_agent_manager import call_manager_plan_llm, validate_and_order_tasks
from backend.agent.multi_agent_messages import build_subtask_messages
from backend.agent.multi_agent_registry import (
    agent_label,
    agent_role_prompt,
    max_agents_per_round,
    skills_for_agent,
)
from backend.agent.multi_agent_summarize import call_summarize_llm
from backend.agent.observation import summarize_observation
from backend.agent.formatter import stream_result_events
from backend.agent.runner import stream_specialist
from backend.trace import log_event


def _latest_user_question(messages: List[Dict[str, str]]) -> str:
    for m in reversed(messages):
        if m.get("role") == "user":
            return str(m.get("content") or "")
    return ""


def _has_structured_auto_analysis(result: Optional[Dict[str, Any]]) -> bool:
    if not isinstance(result, dict):
        return False
    data = result.get("data")
    return isinstance(data, dict) and (
        isinstance(data.get("analysis_proposal"), dict)
        or isinstance(data.get("dashboard_middleware"), dict)
    )


async def stream_chat_multi_agent(
    messages: List[Dict[str, str]],
    trace_id: str = "",
    skill_db_overrides: Optional[Dict[str, str]] = None,
    memory_block: Optional[str] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Manager pattern:
      1. Manager LLM emits JSON subtasks (agent_id, handoff, optional depends_on)
      2. Each subtask runs stream_specialist with filtered skills + subagent ReAct prompt
      3. Synthesis LLM (Manager voice) merges observations for the user
    Falls back to single-agent mode if planning fails or tasks invalid.
    """
    log_event(
        trace_id,
        "agent.multi",
        "started",
        payload={"message_count": len(messages)},
    )
    plan = await call_manager_plan_llm(messages, trace_id=trace_id)
    cap = max_agents_per_round()
    ordered = None
    if plan and isinstance(plan, dict):
        ordered = validate_and_order_tasks(plan.get("tasks", []), cap)
        dr = plan.get("decomposition_reason") or ""
        yield {
            "type": "thinking",
            "content": f"[Manager-规划] {dr}".strip() or "[Manager-规划] 已完成子任务编排。",
        }
        summary = plan.get("user_intent_summary")
        if isinstance(summary, str) and summary.strip():
            yield {"type": "thinking", "content": f"[Manager-规划] 意图：{summary.strip()}"}

    if not ordered:
        log_event(trace_id, "agent.multi", "fallback_single", level="INFO")
        from backend.agent.runner import stream_chat as _single

        async for event in _single(
            messages,
            trace_id=trace_id,
            skill_db_overrides=skill_db_overrides,
            memory_block=memory_block,
            multi_agents=False,
        ):
            yield event
        return

    obs_by_idx: Dict[int, str] = {}
    blocks: List[Dict[str, str]] = []
    last_result: Optional[Dict[str, Any]] = None
    last_skill_name: Optional[str] = None

    for orig_idx, task in ordered:
        agent_id = str(task["agent_id"])
        label = agent_label(agent_id)
        role = agent_role_prompt(agent_id)
        docs = skills_for_agent(agent_id)
        if not docs:
            yield {"type": "thinking", "content": f"[{label}] 无可用技能，跳过。"}
            continue

        dep = task.get("depends_on")
        prior = obs_by_idx.get(int(dep)) if type(dep) is int else None
        sub_messages = build_subtask_messages(
            messages,
            str(task["handoff_instruction"]),
            prior,
        )
        sink: Dict[str, Any] = {}
        acc_text = ""

        async for event in stream_specialist(
            sub_messages,
            docs,
            role_prompt=role,
            trace_id=trace_id,
            skill_db_overrides=skill_db_overrides,
            memory_block=memory_block,
            result_sink=sink,
            subagent_mode=True,
        ):
            et = event.get("type")
            if et == "thinking":
                c = str(event.get("content") or "")
                yield {"type": "thinking", "content": f"[{label}] {c}"}
            elif et == "text":
                acc_text += str(event.get("content") or "")
            elif et == "chart":
                pass
            elif et == "kpi_cards":
                pass
            elif et == "error":
                yield {
                    "type": "thinking",
                    "content": f"[{label}] 错误：{event.get('content')}",
                }

        lr = sink.get("last_result")
        lsn = sink.get("last_skill_name")
        if isinstance(lr, dict):
            last_result = lr
        if isinstance(lsn, str) and lsn:
            last_skill_name = lsn
        obs = (
            summarize_observation(str(lsn or "skill"), lr)
            if isinstance(lr, dict)
            else (acc_text[:1200] if acc_text else "（无工具结果）")
        )
        obs_by_idx[orig_idx] = obs
        blocks.append(
            {
                "agent": agent_id,
                "label": label,
                "handoff_instruction": str(task["handoff_instruction"]),
                "observation": obs,
            }
        )

    q = _latest_user_question(messages)
    if _has_structured_auto_analysis(last_result):
        yield {"type": "thinking", "content": "[Manager-汇总] 已生成结构化分析中间件，直接输出。"}
        async for event in stream_result_events(
            last_skill_name or "chatbi-auto-analysis", {}, last_result or {}
        ):
            yield event
        log_event(
            trace_id,
            "agent.multi",
            "completed",
            payload={"tasks": len(ordered), "short_circuit": "auto_analysis_middleware"},
        )
        yield {"type": "done", "content": None}
        return

    yield {"type": "thinking", "content": "[Manager-汇总] 正在整合各子任务结论..."}
    synth = await call_summarize_llm(q, blocks, trace_id=trace_id)
    if not synth or not isinstance(synth, dict):
        yield {
            "type": "text",
            "content": "汇总阶段未能生成回答，请重试或关闭多专线模式。",
        }
        log_event(trace_id, "agent.multi", "summary_empty", level="WARN")
        yield {"type": "done", "content": None}
        return

    skill_label = last_skill_name or "chatbi-semantic-query"
    merged: Dict[str, Any] = dict(last_result) if last_result else {}
    if synth.get("text"):
        merged["text"] = synth["text"]

    yield {"type": "thinking", "content": "[Manager-汇总] 正在输出最终结论..."}

    async for event in stream_result_events(skill_label, synth, merged):
        yield event

    log_event(
        trace_id,
        "agent.multi",
        "completed",
        payload={"tasks": len(ordered)},
    )
    yield {"type": "done", "content": None}
