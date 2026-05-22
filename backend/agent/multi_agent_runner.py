"""Multi-agent orchestration: Manager multi-round plan → specialists → synthesis."""

from __future__ import annotations

from typing import Any, AsyncGenerator, Dict, List, Optional

from backend.agent.abort_async import ChatAbortedError
from backend.agent.harness_events import (
    log_harness_multi_batch_authorized,
    log_harness_multi_batch_validated,
    log_harness_decision_content_audit,
    log_harness_multi_finish,
    log_harness_multi_summary_dependency_unmet,
    log_harness_multi_task_executing,
    log_harness_multi_task_observation,
    log_harness_rejected,
)
from backend.agent.harness_state import HarnessState
from backend.agent.multi_agent_manager import call_manager_plan_llm, validate_and_order_tasks
from backend.agent.multi_agent_messages import build_subtask_messages
from backend.agent.multi_agent_registry import (
    agent_label,
    agent_role_prompt,
    max_agents_per_round,
    max_manager_rounds,
    preferred_skill_slugs_for_agent,
    skills_for_agent,
)
from backend.agent.multi_agent_summarize import call_summarize_llm
from backend.agent.observation import summarize_observation
from backend.agent.skill_history import (
    build_combined_observation,
    get_skill_executions,
    merge_results_for_finish,
)
from backend.agent.formatter import stream_result_events
from backend.agent.decision_content_audit import audit_decision_result
from backend.agent.runner import stream_specialist
from backend.agent.data_source_intent import resolve_data_source
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


def _has_rows_result(result: Optional[Dict[str, Any]]) -> bool:
    if not isinstance(result, dict):
        return False
    data = result.get("data")
    return isinstance(data, dict) and isinstance(data.get("rows"), list) and bool(data["rows"])


def _harness_observation_metadata(result: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(result, dict):
        return {}
    data = result.get("data")
    if not isinstance(data, dict):
        return {}
    metadata: Dict[str, Any] = {}
    if isinstance(data.get("analysis_mode"), str):
        metadata["analysis_mode"] = data["analysis_mode"]
    if isinstance(data.get("status"), str):
        metadata["status"] = data["status"]
    if isinstance(data.get("row_count"), int):
        metadata["row_count"] = data["row_count"]
    plan_summary = data.get("plan_summary")
    if isinstance(plan_summary, dict):
        metadata["plan_summary"] = {
            "metric": plan_summary.get("metric"),
            "dimensions": plan_summary.get("dimensions"),
            "time_filter": plan_summary.get("time_filter"),
            "order_by_metric_desc": plan_summary.get("order_by_metric_desc"),
            "limit": plan_summary.get("limit"),
        }
    if isinstance(result.get("chart_plan"), dict):
        metadata["has_chart_plan"] = True
    kpis = result.get("kpis")
    if isinstance(kpis, list):
        metadata["kpi_count"] = len(kpis)
    if str(result.get("kind") or "") == "decision":
        metadata["decision_content_audit"] = audit_decision_result(result)
    if isinstance(data.get("dashboard_middleware"), dict):
        metadata["dashboard_ready"] = True
    return metadata


def _decision_audit_from_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    audit = metadata.get("decision_content_audit")
    return audit if isinstance(audit, dict) else {}


def _dependency_warning_from_observation(observation: str) -> str:
    text = observation.strip()
    if not text:
        return ""
    hints = (
        "缺少",
        "待补数据",
        "无法生成建议",
        "尚未获得工具结果",
        "尚未获取工具结果",
        "无工具结果",
        "需要先",
        "请先",
    )
    if any(hint in text for hint in hints):
        return text[:200]
    return ""


async def stream_chat_multi_agent(
    messages: List[Dict[str, str]],
    trace_id: str = "",
    skill_db_overrides: Optional[Dict[str, str]] = None,
    memory_block: Optional[str] = None,
    session_id: Optional[int] = None,
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
    all_skill_executions: List[Dict[str, Any]] = []
    summary_dependency_warnings: List[str] = []
    harness_state = HarnessState(
        trace_id=trace_id,
        user_text=_latest_user_question(messages),
        max_steps=n_rounds,
        session_id=session_id,
        mode="multi",
    )

    for rnd in range(1, n_rounds + 1):
        harness_state.begin_step(rnd)
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
                session_id=session_id,
            )
        except ChatAbortedError:
            log_event(trace_id, "agent.multi", "aborted", level="INFO")
            yield {"type": "thinking", "content": "用户中止了查询。"}
            yield {"type": "done", "content": None}
            return
        if not plan or not isinstance(plan, dict):
            harness_state.record_rejection("Manager 未返回有效的多专线规划。")
            log_harness_rejected(
                trace_id,
                harness_state,
                category="schema_rejected",
                reason="Manager 未返回有效的多专线规划。",
            )
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
            harness_state.record_rejection("Manager 子任务未通过 Harness 校验。")
            log_harness_rejected(
                trace_id,
                harness_state,
                category="policy_rejected",
                reason="Manager 子任务未通过 Harness 校验。",
            )
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
        harness_state.record_accept()
        log_harness_multi_batch_validated(
            trace_id,
            harness_state,
            round_index=rnd,
            task_count=len(ordered),
            agent_ids=[str(task["agent_id"]) for _, task in ordered],
        )
        log_harness_multi_batch_authorized(
            trace_id,
            harness_state,
            round_index=rnd,
            task_count=len(ordered),
            agent_ids=[str(task["agent_id"]) for _, task in ordered],
        )

        if _is_aborted(trace_id):
            log_event(trace_id, "agent.multi", "aborted", level="INFO")
            yield {"type": "thinking", "content": "用户中止了查询。"}
            yield {"type": "done", "content": None}
            return

        obs_by_idx: Dict[int, str] = {}
        skill_failure_this_batch = False
        batch_data_intent = resolve_data_source(messages)
        for orig_idx, task in ordered:
            agent_id = str(task["agent_id"])
            label = agent_label(agent_id)
            role = agent_role_prompt(agent_id)
            docs = skills_for_agent(agent_id)
            if not docs:
                harness_state.record_rejection(f"{agent_id} 当前无可用技能。")
                log_harness_rejected(
                    trace_id,
                    harness_state,
                    category="policy_rejected",
                    reason=f"{agent_id} 当前无可用技能。",
                )
                yield {"type": "thinking", "content": f"[{label}] 无可用技能，跳过。"}
                continue

            dep = task.get("depends_on")
            prior = obs_by_idx.get(int(dep)) if type(dep) is int else None
            log_harness_multi_task_executing(
                trace_id,
                harness_state,
                round_index=rnd,
                task_index=orig_idx,
                agent_id=agent_id,
                handoff_instruction=str(task["handoff_instruction"]),
                depends_on=dep if type(dep) is int else None,
            )
            sub_messages = build_subtask_messages(
                messages,
                str(task["handoff_instruction"]),
                prior,
                data_source_intent=batch_data_intent,
            )
            sink: Dict[str, Any] = {}
            acc_text = ""
            task_failed = False

            async for event in stream_specialist(
                sub_messages,
                docs,
                preferred_skill_slugs=preferred_skill_slugs_for_agent(agent_id),
                role_prompt=role,
                trace_id=trace_id,
                skill_db_overrides=skill_db_overrides,
                memory_block=memory_block,
                result_sink=sink,
                subagent_mode=True,
                specialist_agent_id=agent_id,
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
                    err_content = str(event.get("content") or "")
                    yield {
                        "type": "thinking",
                        "content": f"[{label}] 错误：{err_content}",
                    }
                    # Track skill-not-found errors for Manager re-planning
                    if "未找到技能" in err_content or "skill_not_in_line" in err_content:
                        task_failed = True
                        skill_failure_this_batch = True
                        missing = err_content.split("未找到技能：")[-1].strip()
                        progress_lines.append(
                            f"[技能缺失提示] {label} 无法执行 skill「{missing}」，"
                            f"该专线不具备此技能。Manager 应在下一轮重新指派到拥有「{missing}」的专线。"
                        )

            lr = sink.get("last_result")
            lsn = sink.get("last_skill_name")
            if isinstance(lr, dict):
                last_result = lr
            if isinstance(lsn, str) and lsn:
                last_skill_name = lsn
            executions = get_skill_executions(sink)
            if executions:
                all_skill_executions.extend(executions)
            obs = (
                build_combined_observation(executions)
                if executions
                else (
                    summarize_observation(str(lsn or "skill"), lr)
                    if isinstance(lr, dict)
                    else (acc_text[:1200] if acc_text else "（无工具结果）")
                )
            )
            # Detect skill-not-found from accumulated text (silent failure case)
            if ("未找到技能" in acc_text or "skill_not_in_line" in acc_text) and not any(
                "技能缺失提示" in line for line in progress_lines
            ):
                skill_failure_this_batch = True
                missing_match = [
                    s for s in acc_text.split("\n") if "未找到技能" in s or "skill_not_in_line" in s
                ]
                if missing_match:
                    line0 = missing_match[0]
                    missing = (
                        line0.split("未找到技能：")[-1].strip()
                        if "未找到技能" in line0
                        else "（见 Observation）"
                    )
                    progress_lines.append(
                        f"[技能缺失提示] {label} 无法执行 skill「{missing}」，"
                        f"该专线不具备此技能。Manager 应在下一轮重新指派到拥有「{missing}」的专线。"
                    )
            if "skill_not_in_line" in obs:
                task_failed = True
                skill_failure_this_batch = True
            obs_by_idx[orig_idx] = obs
            if isinstance(lsn, str) and lsn and isinstance(lr, dict):
                harness_state.record_skill(lsn, lr)
            else:
                harness_state.record_accept()
            result_kind = str(lr.get("kind") or "") if isinstance(lr, dict) else ""
            has_result = bool(executions) or isinstance(lr, dict)
            has_rows = _has_rows_result(lr)
            has_auto_analysis = _has_structured_auto_analysis(lr)
            dependency_warning = _dependency_warning_from_observation(obs)
            if dependency_warning:
                summary_dependency_warnings.append(f"{label}: {dependency_warning}")
            metadata = _harness_observation_metadata(lr)
            log_harness_multi_task_observation(
                trace_id,
                harness_state,
                round_index=rnd,
                task_index=orig_idx,
                agent_id=agent_id,
                observation=obs,
                last_skill_name=lsn if isinstance(lsn, str) and lsn else None,
                ok=not task_failed,
                result_kind=result_kind,
                has_result=has_result,
                has_rows=has_rows,
                has_auto_analysis=has_auto_analysis,
                dependency_warning=dependency_warning,
                metadata=metadata,
            )
            audit = _decision_audit_from_metadata(metadata)
            if audit:
                log_harness_decision_content_audit(
                    trace_id,
                    harness_state,
                    skill_name=lsn if isinstance(lsn, str) and lsn else f"specialist:{agent_id}",
                    audit=audit,
                    agent_id=agent_id,
                )
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
                merged_auto = merge_results_for_finish(
                    all_skill_executions or get_skill_executions(sink),
                    {},
                    last_skill_name,
                )
                async for event in stream_result_events(
                    last_skill_name or "chatbi-auto-analysis",
                    {},
                    merged_auto if merged_auto else (last_result or {}),
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
                log_harness_multi_finish(
                    trace_id,
                    harness_state,
                    block_count=len(all_blocks),
                    round_count=rnd,
                )
                yield {"type": "done", "content": None}
                return

        if rnd >= n_rounds:
            break
        fin = plan.get("finalize_after_this_batch")
        stop_planning = fin is None or bool(fin)
        if skill_failure_this_batch and rnd < n_rounds:
            stop_planning = False
            yield {
                "type": "thinking",
                "content": "[Manager-规划] 子专线技能调用失败，将进行下一轮重新指派。",
            }
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
    if summary_dependency_warnings:
        log_harness_multi_summary_dependency_unmet(
            trace_id,
            harness_state,
            warnings=summary_dependency_warnings,
        )
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
    merged = merge_results_for_finish(
        all_skill_executions,
        synth,
        last_skill_name,
    )
    if not all_skill_executions and isinstance(last_result, dict):
        merged = dict(last_result)
        if synth.get("text"):
            merged["text"] = synth["text"]

    yield {"type": "thinking", "content": "[Manager-汇总] 正在输出最终结论..."}

    async for event in stream_result_events(skill_label, synth, merged):
        yield event

    log_harness_multi_finish(
        trace_id,
        harness_state,
        block_count=len(all_blocks),
        round_count=min(n_rounds, max(1, len({block["round"] for block in all_blocks}))),
    )
    log_event(
        trace_id,
        "agent.multi",
        "completed",
        payload={"blocks": len(all_blocks)},
    )
    yield {"type": "done", "content": None}
