"""Multi-agent orchestration: Manager multi-round plan → specialists → synthesis."""

from __future__ import annotations

from typing import Any, AsyncGenerator, Dict, List, Optional

from backend.agent.abort_async import ChatAbortedError
from backend.agent.multi_agent_manager import call_manager_plan_llm, validate_and_order_tasks
from backend.agent.multi_agent_messages import build_subtask_messages
from backend.agent.multi_agent_registry import (
    agent_label,
    agent_role_prompt,
    max_agents_per_round,
    max_manager_rounds,
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
    Manager pattern (multi-round):
      1. Manager LLM plans batch of subtasks (may repeat with Observation digest).
      2. Each subtask runs stream_specialist (subagent ReAct / legacy).
      3. Synthesis LLM merges all batches for the user.
    """
    from backend.agent.abort_state import is_aborted as _is_aborted

    log_event(
        trace_id,
        "agent.multi",
        "started",
        payload={"message_count": len(messages)},
    )
    cap = max_agents_per_round()
    n_rounds = max_manager_rounds()
    all_blocks: List[Dict[str, str]] = []
    progress_lines: List[str] = []
    last_result: Optional[Dict[str, Any]] = None
    last_skill_name: Optional[str] = None

    for rnd in range(1, n_rounds + 1):
        if _is_aborted(trace_id):
            log_event(trace_id, "agent.multi", "aborted", level="INFO")
            yield {"type": "thinking", "content": "用户中止了查询。"}
            yield {"type": "done", "content": None}
            return

        digest = "\n\n".join(progress_lines)
        try:
            plan = await call_manager_plan_llm(
                messages,
                trace_id=trace_id,
                round_index=rnd,
                progress_digest=digest,
            )
        except ChatAbortedError:
            log_event(trace_id, "agent.multi", "aborted", level="INFO")
            yield {"type": "thinking", "content": "用户中止了查询。"}
            yield {"type": "done", "content": None}
            return
        if not plan or not isinstance(plan, dict):
            if rnd == 1:
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
            break

        tag = f"[Manager-规划 R{rnd}]" if rnd > 1 else "[Manager-规划]"
        dr = plan.get("decomposition_reason") or ""
        yield {
            "type": "thinking",
            "content": f"{tag} {dr}".strip() or f"{tag} 已完成子任务编排。",
        }
        summary = plan.get("user_intent_summary")
        if isinstance(summary, str) and summary.strip():
            yield {"type": "thinking", "content": f"{tag} 意图：{summary.strip()}"}

        raw_tasks = plan.get("tasks") if isinstance(plan.get("tasks"), list) else []
        if rnd > 1:
            if not raw_tasks and bool(plan.get("ready_for_final_answer")):
                yield {
                    "type": "thinking",
                    "content": "[Manager-规划] 不再派发子任务，进入汇总。",
                }
                break
            if not raw_tasks:
                yield {
                    "type": "thinking",
                    "content": "[Manager-规划] 本轮未给出子任务，进入汇总。",
                }
                break

        ordered = validate_and_order_tasks(raw_tasks, cap)
        if ordered is None:
            if rnd == 1:
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
            yield {
                "type": "thinking",
                "content": "[Manager-规划] 子任务校验失败，按已有结果汇总。",
            }
            break

        if _is_aborted(trace_id):
            log_event(trace_id, "agent.multi", "aborted", level="INFO")
            yield {"type": "thinking", "content": "用户中止了查询。"}
            yield {"type": "done", "content": None}
            return

        obs_by_idx: Dict[int, str] = {}
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
                if _is_aborted(trace_id):
                    log_event(trace_id, "agent.multi", "aborted", level="INFO")
                    yield {"type": "thinking", "content": "用户中止了查询。"}
                    yield {"type": "done", "content": None}
                    return
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
            hi = str(task["handoff_instruction"])
            progress_lines.append(
                f"[第{rnd}轮·{label}] 交办：{hi[:500]}\nObservation：{obs[:2000]}"
            )
            all_blocks.append(
                {
                    "agent": agent_id,
                    "label": label,
                    "handoff_instruction": hi,
                    "observation": obs,
                    "round": str(rnd),
                }
            )

            if _has_structured_auto_analysis(last_result):
                yield {
                    "type": "thinking",
                    "content": "[Manager-汇总] 已生成结构化分析中间件，直接输出。",
                }
                async for event in stream_result_events(
                    last_skill_name or "chatbi-auto-analysis", {}, last_result or {}
                ):
                    yield event
                log_event(
                    trace_id,
                    "agent.multi",
                    "completed",
                    payload={
                        "rounds": rnd,
                        "blocks": len(all_blocks),
                        "short_circuit": "auto_analysis_middleware",
                    },
                )
                yield {"type": "done", "content": None}
                return

        if rnd >= n_rounds:
            break
        fin = plan.get("finalize_after_this_batch")
        stop_planning = fin is None or bool(fin)
        if stop_planning:
            yield {
                "type": "thinking",
                "content": "[Manager-规划] 本批完成后进入汇总。",
            }
            break
        yield {
            "type": "thinking",
            "content": "[Manager-规划] 将继续下一轮规划。",
        }

    if not all_blocks:
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

    q = _latest_user_question(messages)
    yield {"type": "thinking", "content": "[Manager-汇总] 正在整合各子任务结论..."}
    try:
        synth = await call_summarize_llm(q, all_blocks, trace_id=trace_id)
    except ChatAbortedError:
        log_event(trace_id, "agent.multi", "aborted", level="INFO")
        yield {"type": "thinking", "content": "用户中止了查询。"}
        yield {"type": "done", "content": None}
        return
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
        payload={"blocks": len(all_blocks)},
    )
    yield {"type": "done", "content": None}
