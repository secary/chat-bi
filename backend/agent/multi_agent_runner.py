"""Multi-agent orchestration: controlled intent routing → audited route transitions."""

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
from backend.agent.multi_agent_intent import (
    build_initial_plan_from_intent,
    build_next_plan_from_intent,
    classify_multi_agent_intent,
    route_sequence_from_intent,
)
from backend.agent.multi_agent_manager import validate_and_order_tasks
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

_DECISION_ROUTE_KEYWORDS = (
    "经营建议",
    "建议",
    "决策意见",
    "管理建议",
    "下一步动作",
    "怎么做",
)

_ROUTE_SEED_AGENT_IDS = {"business_advisor", "viz_board"}
_TERMINAL_ROUTE_AGENT_IDS = {"business_advisor"}


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


def _wants_decision_route(user_question: str) -> bool:
    text = user_question.strip()
    return bool(text) and any(keyword in text for keyword in _DECISION_ROUTE_KEYWORDS)


def _has_decision_result(
    result: Optional[Dict[str, Any]],
    skill_name: Optional[str],
) -> bool:
    if not isinstance(result, dict):
        return False
    if skill_name == "chatbi-decision-advisor":
        return True
    return str(result.get("kind") or "") == "decision"


def _build_audited_followup_plan(
    *,
    user_question: str,
    all_blocks: List[Dict[str, str]],
    last_result: Optional[Dict[str, Any]],
    last_skill_name: Optional[str],
    round_index: int,
) -> Optional[Dict[str, Any]]:
    if round_index <= 1:
        return None
    if not _wants_decision_route(user_question):
        return None
    if _has_decision_result(last_result, last_skill_name):
        return None
    if not _has_rows_result(last_result):
        return None
    if any(block.get("agent") == "business_advisor" for block in all_blocks):
        return None
    return {
        "user_intent_summary": "基于现有事实生成经营建议",
        "decomposition_reason": "Harness 多路由：问数结果已就绪，直接切换到经营建议专线。",
        "tasks": [
            {
                "agent_id": "business_advisor",
                "handoff_instruction": (
                    "基于前置问数结果直接生成经营建议，优先引用已有 rows 与结构化事实，"
                    "不要重复问数；若事实不足，请明确指出缺口。"
                ),
                "depends_on": None,
            }
        ],
        "finalize_after_this_batch": True,
        "routed_by": "harness",
    }


def _seed_result_for_route(
    agent_id: str,
    prior_state: Optional[Dict[str, Any]],
    last_result: Optional[Dict[str, Any]],
    last_skill_name: Optional[str],
) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    if isinstance(prior_state, dict):
        prior_result = prior_state.get("last_result")
        prior_skill = prior_state.get("last_skill_name")
        return (
            prior_result if isinstance(prior_result, dict) else None,
            str(prior_skill) if isinstance(prior_skill, str) and prior_skill else None,
        )
    if agent_id in _ROUTE_SEED_AGENT_IDS and isinstance(last_result, dict):
        return last_result, last_skill_name if isinstance(last_skill_name, str) else None
    return None, None


def _route_objective_completed(
    *,
    user_question: str,
    all_blocks: List[Dict[str, str]],
    last_result: Optional[Dict[str, Any]],
    last_skill_name: Optional[str],
    controlled_intent: Optional[Dict[str, Any]] = None,
) -> bool:
    if isinstance(controlled_intent, dict):
        required = route_sequence_from_intent(controlled_intent)
        completed = {str(block.get("agent") or "") for block in all_blocks}
        return bool(required) and all(route in completed for route in required)
    if _wants_decision_route(user_question) and _has_decision_result(last_result, last_skill_name):
        return any(block.get("agent") in _TERMINAL_ROUTE_AGENT_IDS for block in all_blocks)
    return False


async def stream_chat_multi_agent(
    messages: List[Dict[str, str]],
    trace_id: str = "",
    skill_db_overrides: Optional[Dict[str, str]] = None,
    memory_block: Optional[str] = None,
    session_id: Optional[int] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Controlled multi-agent pattern:
      1. Deterministic intent routing selects the current specialist route.
      2. Harness generates and audits internal specialist tasks.
      3. Synthesis LLM merges completed specialist observations for the user.
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
    obs_by_idx: Dict[int, str] = {}
    result_by_idx: Dict[int, Dict[str, Any]] = {}
    last_result: Optional[Dict[str, Any]] = None
    last_skill_name: Optional[str] = None
    all_skill_executions: List[Dict[str, Any]] = []
    summary_dependency_warnings: List[str] = []
    forced_followup_plan: Optional[Dict[str, Any]] = None
    controlled_intent = classify_multi_agent_intent(messages)
    public_progress_emitted: set[str] = set()
    harness_state = HarnessState(
        trace_id=trace_id,
        user_text=_latest_user_question(messages),
        max_steps=n_rounds,
        session_id=session_id,
        mode="multi",
    )

    def public_progress(key: str, content: str) -> Optional[Dict[str, str]]:
        if key in public_progress_emitted:
            return None
        public_progress_emitted.add(key)
        return {"type": "thinking", "content": content}

    event = public_progress("understand", "正在理解问题...")
    if event:
        yield event

    for rnd in range(1, n_rounds + 1):
        harness_state.begin_step(rnd)
        if _is_aborted(trace_id):
            log_event(trace_id, "agent.multi", "aborted", level="INFO")
            yield {"type": "thinking", "content": "用户中止了查询。"}
            yield {"type": "done", "content": None}
            return

        if forced_followup_plan is not None:
            plan = forced_followup_plan
            forced_followup_plan = None
            log_event(
                trace_id,
                "agent.harness",
                "route_transition_selected",
                payload={
                    "mode": "multi",
                    "step": rnd,
                    "from_skill": last_skill_name,
                    "to_agent": plan["tasks"][0]["agent_id"],
                    "reason": plan.get("decomposition_reason"),
                },
            )
        elif rnd == 1 and isinstance(controlled_intent, dict):
            plan = build_initial_plan_from_intent(controlled_intent)
            if not plan:
                break
            log_event(
                trace_id,
                "agent.harness",
                "route_intent_classified",
                payload={
                    "mode": "multi",
                    "step": rnd,
                    "intent_type": controlled_intent.get("intent_type"),
                    "current_route": controlled_intent.get("current_route"),
                    "route_sequence": route_sequence_from_intent(controlled_intent),
                    "final_outputs": controlled_intent.get("final_outputs"),
                    "summary": controlled_intent.get("summary"),
                },
            )
        else:
            if rnd == 1:
                harness_state.record_rejection("受控意图识别未命中多专线路由。")
                log_harness_rejected(
                    trace_id,
                    harness_state,
                    category="intent_unmatched",
                    reason="受控意图识别未命中多专线路由。",
                )
            break

        raw_tasks = plan.get("tasks") if isinstance(plan.get("tasks"), list) else []
        if rnd > 1:
            if not raw_tasks and bool(plan.get("ready_for_final_answer")):
                break
            if not raw_tasks:
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
                event = public_progress("retry", "正在调整处理方式...")
                if event:
                    yield event
                continue

            dep = task.get("depends_on")
            prior = obs_by_idx.get(int(dep)) if type(dep) is int else None
            prior_state = result_by_idx.get(int(dep)) if type(dep) is int else None
            seeded_result, seeded_skill_name = _seed_result_for_route(
                agent_id,
                prior_state,
                last_result,
                last_skill_name,
            )
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
            event = public_progress("process", "正在处理信息...")
            if event:
                yield event

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
                initial_last_result=seeded_result,
                initial_last_skill_name=seeded_skill_name,
            ):
                if _is_aborted(trace_id):
                    log_event(trace_id, "agent.multi", "aborted", level="INFO")
                    yield {"type": "thinking", "content": "用户中止了查询。"}
                    yield {"type": "done", "content": None}
                    return
                et = event.get("type")
                if et == "thinking":
                    pass
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
                        "content": "处理时遇到问题，正在尝试调整...",
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
            if isinstance(lr, dict):
                result_by_idx[orig_idx] = {
                    "last_result": lr,
                    "last_skill_name": lsn if isinstance(lsn, str) and lsn else None,
                }
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
                merged_auto = merge_results_for_finish(
                    all_skill_executions or get_skill_executions(sink),
                    {},
                    last_skill_name,
                )
                async for event in stream_result_events(
                    last_skill_name or "chatbi-auto-analysis",
                    {},
                    merged_auto if merged_auto else (last_result or {}),
                    include_thinking=False,
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

        if _route_objective_completed(
            user_question=harness_state.user_text,
            all_blocks=all_blocks,
            last_result=last_result,
            last_skill_name=last_skill_name,
            controlled_intent=controlled_intent,
        ):
            log_event(
                trace_id,
                "agent.harness",
                "route_objective_completed",
                payload={
                    "mode": "multi",
                    "step": rnd,
                    "last_skill_name": last_skill_name,
                    "completed_agents": [block.get("agent") for block in all_blocks],
                },
            )
            break

        if rnd >= n_rounds:
            break
        completed_agents = [str(block.get("agent") or "") for block in all_blocks]
        if controlled_intent is not None:
            forced_followup_plan = build_next_plan_from_intent(
                controlled_intent,
                completed_agents=completed_agents,
            )
        else:
            forced_followup_plan = _build_audited_followup_plan(
                user_question=harness_state.user_text,
                all_blocks=all_blocks,
                last_result=last_result,
                last_skill_name=last_skill_name,
                round_index=rnd + 1,
            )
        if forced_followup_plan is not None:
            continue
        fin = plan.get("finalize_after_this_batch")
        stop_planning = fin is None or bool(fin)
        if skill_failure_this_batch and rnd < n_rounds:
            stop_planning = False
        if stop_planning:
            break

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
    event = public_progress("summarize", "正在整理答案...")
    if event:
        yield event
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

    async for event in stream_result_events(skill_label, synth, merged, include_thinking=False):
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
