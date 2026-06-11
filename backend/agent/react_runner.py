from __future__ import annotations

import json
import tempfile
from typing import Any, AsyncGenerator, Dict, List, Optional

from backend.agent.context_window import build_react_context
from backend.agent.decision_content_audit import audit_decision_result
from backend.agent.executor import (
    find_skill,
    latest_user_upload_path,
    run_script,
    skill_result_log_payload,
    skill_args_for_execution,
)
from backend.agent.formatter import stream_result_events
from backend.agent.harness_events import (
    log_harness_authorized,
    log_harness_decision_content_audit,
    log_harness_executing,
    log_harness_finish,
    log_harness_observation,
    log_harness_rejected,
    log_harness_validated,
)
from backend.agent.harness_policy import authorize_action, rejection_observation
from backend.agent.harness_schema import HarnessAction, validate_harness_action
from backend.agent.harness_state import HarnessState
from backend.agent.intent_guard import small_talk_reply, should_skip_skill_for_message
from backend.agent.observation import summarize_observation
from backend.agent.skill_history import (
    clear_skill_sink,
    get_skill_executions,
    merge_results_for_finish,
    record_skill_execution,
    sync_skill_sink,
)
from backend.agent.abort_async import ChatAbortedError
from backend.agent.data_source_intent import DataSourceIntent, resolve_data_source
from backend.agent.planner import call_llm_for_react_step
from backend.agent.prompt_builder import (
    SkillDoc,
    build_react_system_prompt,
    scan_skills_enabled,
)
from backend.agent.prompt_subagent import build_react_system_prompt_for_subagent
from backend.agent.query_decision import is_query_plus_decision_text
from backend.agent.react_followup import run_decision_followup
from backend.agent.upload_context import cache_file_data, get_cached_file_data, get_cached_rows
from backend.config import settings
from backend.trace import log_event

OBS_HEADER = "以下为工具执行后的 Observation（JSON 摘要），请基于事实继续推理：\n"


def _finish_merged(
    result_sink: Optional[Dict[str, Any]],
    finish_plan: Dict[str, Any],
    last_skill_name: Optional[str],
    last_result: Optional[Dict[str, Any]] = None,
    local_executions: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    executions = get_skill_executions(result_sink) or (local_executions or [])
    if not executions and isinstance(last_result, dict):
        from backend.agent.skill_history import merge_finish_result

        return merge_finish_result(finish_plan, last_result, last_skill_name)
    return merge_results_for_finish(executions, finish_plan, last_skill_name)


def _rows_for_followup_chart(result: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not isinstance(result, dict):
        return []
    data = result.get("data")
    if not isinstance(data, dict):
        return []
    rows = data.get("rows")
    if isinstance(rows, list) and rows:
        return rows
    preview_rows = data.get("preview_rows")
    if isinstance(preview_rows, list) and preview_rows:
        return preview_rows
    return []


def _is_file_ingestion_result(result: Optional[Dict[str, Any]]) -> bool:
    return isinstance(result, dict) and str(result.get("kind") or "") == "file_ingestion"


def _file_ingestion_result_path(result: Optional[Dict[str, Any]]) -> str:
    if not isinstance(result, dict):
        return ""
    data = result.get("data")
    if not isinstance(data, dict):
        return ""
    return str(data.get("file") or "")


def _should_short_circuit_repeated_file_ingestion(
    skill_name: str,
    args: List[str],
    last_skill_name: Optional[str],
    last_result: Optional[Dict[str, Any]],
    messages: Optional[List[Dict[str, str]]] = None,
) -> bool:
    if skill_name != "chatbi-file-ingestion" or last_skill_name != "chatbi-file-ingestion":
        return False
    if not _is_file_ingestion_result(last_result):
        return False
    current_path = str(args[0]) if args else ""
    previous_path = _file_ingestion_result_path(last_result)
    if bool(current_path) and current_path == previous_path:
        return True
    if messages:
        upload_path = latest_user_upload_path(messages)
        if upload_path and get_cached_file_data(upload_path):
            return True
    return False


def _chart_recommendation_args(
    user_text: str,
    plan_args: List[str],
    last_result: Optional[Dict[str, Any]],
) -> List[str]:
    rows = _rows_for_followup_chart(last_result)
    if not rows:
        return plan_args or [user_text]
    payload = {"question": user_text, "rows": rows}
    return [json.dumps(payload, ensure_ascii=False)]


def _latest_analysis_proposal(messages: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    for message in reversed(messages):
        if message.get("role") != "assistant":
            continue
        proposal = message.get("analysisProposal")
        if isinstance(proposal, dict):
            return proposal
    return None


def _auto_analysis_args(
    user_text: str,
    plan_args: List[str],
    last_result: Optional[Dict[str, Any]],
    cached_rows: Optional[List[Dict[str, Any]]] = None,
    column_labels: Optional[Dict[str, Any]] = None,
    proposal: Optional[Dict[str, Any]] = None,
) -> List[str]:
    rows = _rows_for_followup_chart(last_result) or (cached_rows or [])
    if not rows:
        return plan_args or [user_text]
    payload: Dict[str, Any] = {"question": user_text, "rows": rows}
    if column_labels:
        payload["column_labels"] = column_labels
    if proposal:
        metric_plans = proposal.get("proposed_metrics")
        if isinstance(metric_plans, list) and metric_plans:
            payload["metric_plans"] = [item for item in metric_plans if isinstance(item, dict)]
    if _is_confirmation_request(user_text):
        payload["mode"] = "execute"
    return ["--input-file", _write_auto_analysis_payload(payload)]


def _is_terminal_auto_analysis_result(skill_name: str, result: Optional[Dict[str, Any]]) -> bool:
    if skill_name != "chatbi-auto-analysis" or not isinstance(result, dict):
        return False
    data = result.get("data")
    if not isinstance(data, dict):
        return False
    if isinstance(data.get("analysis_proposal"), dict):
        return True
    if isinstance(data.get("dashboard_middleware"), dict):
        return True
    return str(data.get("status") or "") in {"need_confirmation", "ready"}


def _harness_observation_extras(result: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(result, dict):
        return {}
    data = result.get("data")
    if not isinstance(data, dict):
        return {}
    extras: Dict[str, Any] = {}
    if isinstance(data.get("analysis_mode"), str):
        extras["analysis_mode"] = data["analysis_mode"]
    if isinstance(data.get("status"), str):
        extras["status"] = data["status"]
    if isinstance(data.get("row_count"), int):
        extras["row_count"] = data["row_count"]
    plan_summary = data.get("plan_summary")
    if isinstance(plan_summary, dict):
        extras["plan_summary"] = {
            "metric": plan_summary.get("metric"),
            "dimensions": plan_summary.get("dimensions"),
            "time_filter": plan_summary.get("time_filter"),
            "order_by_metric_desc": plan_summary.get("order_by_metric_desc"),
            "limit": plan_summary.get("limit"),
        }
    rows = data.get("rows")
    if isinstance(rows, list):
        extras["has_rows"] = bool(rows)
        extras.setdefault("row_count", len(rows))
    if isinstance(result.get("chart_plan"), dict):
        extras["has_chart_plan"] = True
    kpis = result.get("kpis")
    if isinstance(kpis, list):
        extras["kpi_count"] = len(kpis)
    if str(result.get("kind") or "") == "decision":
        extras["decision_content_audit"] = audit_decision_result(result)
    if isinstance(data.get("dashboard_middleware"), dict):
        extras["has_auto_analysis"] = True
        extras["dashboard_ready"] = True
    if isinstance(data.get("analysis_proposal"), dict):
        extras["has_auto_analysis"] = True
    return extras


def _decision_audit_from_extras(extras: Dict[str, Any]) -> Dict[str, Any]:
    audit = extras.get("decision_content_audit")
    return audit if isinstance(audit, dict) else {}


def _write_auto_analysis_payload(payload: Dict[str, Any]) -> str:
    handle = tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        prefix="chatbi-auto-analysis-",
        suffix=".json",
        delete=False,
    )
    with handle:
        json.dump(payload, handle, ensure_ascii=False)
    return handle.name


def _has_upload_context(messages: List[Dict[str, str]]) -> bool:
    return bool(latest_user_upload_path(messages))


def _is_visual_request(text: str) -> bool:
    markers = ("画图", "图表", "可视化", "展示")
    return bool(text) and any(marker in text for marker in markers)


def _is_auto_analysis_request(text: str) -> bool:
    markers = (
        "分析",
        "指标",
        "看板",
        "仪表盘",
        "dashboard",
        "采纳",
        "确认",
        "roi",
        "ROI",
        "留存",
        "不良",
        "逾期",
        "趋势",
    )
    return bool(text) and any(marker in text for marker in markers)


def _is_confirmation_request(text: str) -> bool:
    return bool(text) and any(word in text for word in ["采纳", "确认", "开始", "生成看板"])


def _enforce_upload_skill(
    skill_name: str,
    user_text: str,
    messages: List[Dict[str, Any]],
    last_result: Optional[Dict[str, Any]],
) -> str:
    if not _has_upload_context(messages):
        return skill_name
    if skill_name == "chatbi-file-ingestion":
        if _is_confirmation_request(user_text) and _latest_analysis_proposal(messages):
            return "chatbi-auto-analysis"
        return skill_name
    if _is_confirmation_request(user_text) and _latest_analysis_proposal(messages):
        return "chatbi-auto-analysis"
    if _rows_for_followup_chart(last_result) and _is_auto_analysis_request(user_text):
        return "chatbi-auto-analysis"
    if skill_name != "chatbi-semantic-query":
        return skill_name
    if resolve_data_source(messages) == DataSourceIntent.DEMO_DATABASE:
        return skill_name
    if _rows_for_followup_chart(last_result) and _is_visual_request(user_text):
        return "chatbi-chart-recommendation"
    return "chatbi-file-ingestion"


def _skill_log_payload(
    skill_name: str,
    skill_doc: SkillDoc,
    *,
    agent_id: Optional[str],
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "skill": skill_name,
        "agent_id": agent_id or "single",
    }
    if extra:
        payload.update(extra)
    return payload


def _force_subagent_converge_on_policy_reject(
    policy: Any,
    *,
    trace_id: str,
    specialist_agent_id: Optional[str],
    result_sink: Optional[Dict[str, Any]],
    last_result: Optional[Dict[str, Any]],
    last_skill_name: Optional[str],
) -> Optional[str]:
    if not specialist_agent_id or not getattr(policy, "suggested_text", ""):
        return None
    suggestion = str(policy.suggested_text).strip()
    if not suggestion:
        return None
    log_event(
        trace_id,
        "agent.runner",
        "completed",
        payload={
            "mode": "react_subagent",
            "action": "forced_converge",
            "agent_id": specialist_agent_id,
        },
    )
    sync_skill_sink(result_sink, last_result, last_skill_name)
    return f"本专线停止继续试错。{suggestion}"


def _result_signature(result: Optional[Dict[str, Any]]) -> tuple[Any, ...]:
    if not isinstance(result, dict):
        return ()
    data = result.get("data")
    rows: List[Dict[str, Any]] = []
    plan_summary: Dict[str, Any] = {}
    if isinstance(data, dict):
        raw_rows = data.get("rows")
        if isinstance(raw_rows, list):
            rows = [row for row in raw_rows[:3] if isinstance(row, dict)]
        raw_plan = data.get("plan_summary")
        if isinstance(raw_plan, dict):
            plan_summary = raw_plan
    row_keys = tuple(sorted(str(key) for row in rows for key in row.keys()))
    row_values = tuple(tuple(sorted((str(k), str(v)) for k, v in row.items())) for row in rows)
    return (
        str(result.get("kind") or ""),
        str(result.get("text") or "")[:240],
        row_keys,
        row_values,
        str(plan_summary.get("metric") or ""),
        tuple(str(item) for item in plan_summary.get("dimensions", []) or []),
        str(plan_summary.get("time_filter") or ""),
    )


def _args_signature(args: List[str]) -> tuple[str, ...]:
    return tuple(str(arg) for arg in args)


def _should_stop_repeated_subagent_skill(
    *,
    subagent_react: bool,
    skill_name: str,
    args: List[str],
    last_skill_name: Optional[str],
    last_result: Optional[Dict[str, Any]],
    repeated_skill_count: int,
    previous_args_signature: tuple[str, ...],
    previous_signature: tuple[Any, ...],
) -> bool:
    if not subagent_react:
        return False
    if skill_name != last_skill_name:
        return False
    if not previous_signature:
        return False
    current_args_signature = _args_signature(args)
    if (
        current_args_signature
        and current_args_signature == previous_args_signature
        and repeated_skill_count >= 1
    ):
        return True
    if repeated_skill_count < 2:
        return False
    return previous_signature == _result_signature(last_result)


async def stream_chat_react(
    messages: List[Dict[str, Any]],
    trace_id: str = "",
    skill_db_overrides: Optional[Dict[str, str]] = None,
    memory_block: Optional[str] = None,
    skill_docs: Optional[List[SkillDoc]] = None,
    preferred_skill_slugs: Optional[List[str]] = None,
    role_prompt: Optional[str] = None,
    result_sink: Optional[Dict[str, Any]] = None,
    subagent_react: bool = False,
    specialist_agent_id: Optional[str] = None,
    session_id: Optional[int] = None,
    user_id: Optional[int] = None,
    initial_last_result: Optional[Dict[str, Any]] = None,
    initial_last_skill_name: Optional[str] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    ReAct multi-step agent loop.
    Each iteration: LLM decides next action {"thought", "action", "skill", "skill_args"} → executes a skill → summarizes observation → repeats.
    Stops when the LLM outputs 'finish/done/answer', or when agent_max_steps is exhausted.
    action == "call_skill", execute Skill，append observation result to working list.
    Auto-runs chatbi-decision-advisor as a followup when query+decision intent is detected.
    """
    log_event(
        trace_id,
        "agent.runner",
        "started",
        payload={
            "message_count": len(messages),
            "mode": "react_subagent" if subagent_react else "react",
        },
    )
    skills = skill_docs if skill_docs is not None else scan_skills_enabled(settings.skills_dir)
    allowed_slugs = {d.skill_dir.name for d in skills}
    user_text = next(
        (str(m.get("content", "")) for m in reversed(messages) if m.get("role") == "user"),
        "",
    )
    upload_path = latest_user_upload_path(messages)
    cached_upload_rows = get_cached_rows(upload_path) if upload_path else []
    latest_proposal = _latest_analysis_proposal(messages)
    if should_skip_skill_for_message(user_text):
        log_event(trace_id, "agent.runner", "skip_skill_small_talk", payload={"mode": "react"})
        clear_skill_sink(result_sink)
        yield {"type": "thinking", "content": "正在准备回复..."}
        yield {"type": "text", "content": small_talk_reply(user_text)}
        yield {"type": "done", "content": None}
        return

    """
    Build the system prompt for the ReAct agent.
    It includes the skills, the role prompt, and the memory block.
    The role prompt is the user's role in the conversation.
    The memory block is the memory of the agent.
    The skills are the skills that the agent can use.
    The system prompt is the prompt that the agent uses to make a decision.
    """
    system_prompt = (
        build_react_system_prompt_for_subagent(skills)
        if subagent_react
        else build_react_system_prompt(skills)
    )
    if role_prompt and role_prompt.strip():
        system_prompt = role_prompt.strip() + "\n\n" + system_prompt
    if memory_block and memory_block.strip():
        system_prompt = memory_block.strip() + "\n\n" + system_prompt

    # Inject sliding window context for long conversation management
    if session_id:
        conversation_context = build_react_context(session_id, user_text, messages, user_id=user_id)
        if conversation_context.strip():
            system_prompt = system_prompt + "\n\n" + conversation_context

    """
    working: 一个消息列表，用于存储对话历史和obs(observation的内容)
    """
    working = [dict(m) for m in messages]
    harness_state = HarnessState(
        trace_id=trace_id,
        user_text=user_text,
        max_steps=settings.agent_max_steps,
        session_id=session_id,
        mode="subagent" if subagent_react else "single",
    )
    harness_state.seed_last_result(initial_last_skill_name, initial_last_result)
    last_skill_name: Optional[str] = (
        initial_last_skill_name if isinstance(initial_last_result, dict) else None
    )
    last_result: Optional[Dict[str, Any]] = (
        dict(initial_last_result) if isinstance(initial_last_result, dict) else None
    )
    local_executions: List[Dict[str, Any]] = []
    called_skills: list[str] = []
    last_result_signature: tuple[Any, ...] = _result_signature(last_result)
    last_skill_args_signature: tuple[str, ...] = ()
    repeated_skill_count = 0
    last_ingestion_rows: List[Dict[str, Any]] = list(cached_upload_rows)
    last_ingestion_column_labels: Optional[Dict[str, Any]] = None

    yield {"type": "thinking", "content": "正在分析您的问题..."}

    """
    ReAct loop:
    LLM decides next action {"thought", "action", "skill", "skill_args"} → executes a skill → summarizes observation → repeats.
    The agent_max_steps is 8 by default. If the agent_max_steps is reached, the agent will return the last result.
    """
    from backend.agent.abort_state import is_aborted as _is_aborted

    for step in range(settings.agent_max_steps):
        harness_state.begin_step(step + 1)
        if _is_aborted(trace_id):
            log_event(trace_id, "agent.runner", "aborted", level="INFO")
            yield {"type": "thinking", "content": "用户中止了查询。"}
            sync_skill_sink(result_sink, last_result, last_skill_name)
            yield {"type": "done", "content": None}
            return

        log_event(
            trace_id,
            "agent.planner",
            "react.step",
            payload={"step": step + 1, "max_steps": settings.agent_max_steps},
        )
        try:
            """
            Call LLM for the next ReAct step.
            将system prompt + 对话的上下文 + skill所执行的结果obs，一起传给LLM，得到下一步的决策。
            LLM 返回 {"thought", "action", "skill", "skill_args"}
            """
            plan = await call_llm_for_react_step(system_prompt, working, trace_id=trace_id)
        except ChatAbortedError:
            log_event(trace_id, "agent.runner", "aborted", level="INFO")
            yield {"type": "thinking", "content": "用户中止了查询。"}
            sync_skill_sink(result_sink, last_result, last_skill_name)
            yield {"type": "done", "content": None}
            return
        except Exception as exc:
            if last_result:
                yield {
                    "type": "thinking",
                    "content": f"模型收尾失败，展示最后一次工具结果：{exc}",
                }
                merged = _finish_merged(
                    result_sink, {}, last_skill_name, last_result, local_executions
                )
                async for event in stream_result_events(last_skill_name or "skill", {}, merged):
                    yield event
                sync_skill_sink(result_sink, last_result, last_skill_name)
                yield {"type": "done", "content": None}
                return
            raise
        if not plan:
            if last_result:
                yield {"type": "thinking", "content": "模型未返回有效 JSON，展示最后一次工具结果。"}
                merged = _finish_merged(
                    result_sink, {}, last_skill_name, last_result, local_executions
                )
                async for event in stream_result_events(last_skill_name or "skill", {}, merged):
                    yield event
                sync_skill_sink(result_sink, last_result, last_skill_name)
                yield {"type": "done", "content": None}
                return
            sync_skill_sink(result_sink, None, None)
            yield {"type": "error", "content": "模型未返回有效 JSON。"}
            yield {"type": "done", "content": None}
            return

        validation = validate_harness_action(plan)
        if not validation.ok:
            harness_state.record_rejection(validation.reason)
            log_harness_rejected(
                trace_id,
                harness_state,
                category="schema_rejected",
                reason=validation.reason,
            )
            working.append(
                {
                    "role": "user",
                    "content": OBS_HEADER + rejection_observation(validation, None),
                }
            )
            if harness_state.should_stop_after_rejection():
                break
            yield {"type": "thinking", "content": "正在调整处理方式..."}
            continue

        action_model = validation.action
        assert action_model is not None
        log_harness_validated(trace_id, harness_state, action_model)
        if action_model.thought:
            yield {"type": "thinking", "content": action_model.thought}

        action = action_model.action
        if action != "call_skill":
            policy = authorize_action(
                action_model,
                harness_state,
                sorted(allowed_slugs),
                messages=messages,
                specialist_agent_id=specialist_agent_id if subagent_react else None,
                preferred_skills=preferred_skill_slugs,
            )
            if not policy.ok:
                harness_state.record_rejection(policy.reason)
                log_harness_rejected(
                    trace_id,
                    harness_state,
                    category="policy_rejected",
                    reason=policy.reason,
                    action=action_model,
                )
                working.append(
                    {
                        "role": "assistant",
                        "content": json.dumps(action_model.raw_plan or plan, ensure_ascii=False),
                    }
                )
                working.append(
                    {
                        "role": "user",
                        "content": OBS_HEADER + rejection_observation(validation, policy),
                    }
                )
                if harness_state.should_stop_after_rejection():
                    break
                yield {"type": "thinking", "content": "正在重新选择更合适的处理方式..."}
                continue

            harness_state.record_accept()
            log_harness_authorized(trace_id, harness_state, action_model)
        if action == "finish":
            log_harness_finish(trace_id, harness_state, action_model)
            yield {"type": "thinking", "content": "正在整理回答..."}
            merged = _finish_merged(
                result_sink, plan, last_skill_name, last_result, local_executions
            )
            skill_label = last_skill_name or "chatbi-semantic-query"
            async for event in stream_result_events(skill_label, plan, merged):
                yield event
            log_event(
                trace_id,
                "agent.runner",
                "completed",
                payload={"mode": "react", "steps": step + 1},
            )
            sync_skill_sink(result_sink, last_result, last_skill_name)
            yield {"type": "done", "content": None}
            return

        if action == "ask_clarification":
            ask_text = action_model.text or "请问还有什么需要帮助的？"
            yield {"type": "thinking", "content": "正在询问补充信息..."}
            yield {"type": "text", "content": ask_text}
            log_event(
                trace_id,
                "agent.runner",
                "completed",
                payload={"mode": "react", "action": "ask", "steps": step + 1},
            )
            sync_skill_sink(result_sink, last_result, last_skill_name)
            yield {"type": "done", "content": None}
            return

        """
        Execute the skill by given the skill name.
        """
        skill_name = action_model.skill or ""
        skill_name = _enforce_upload_skill(skill_name, user_text, messages, last_result)
        # When auto-analysis is called without any row data but a file was uploaded,
        # redirect to file-ingestion first so rows are available on the next step.
        if (
            skill_name == "chatbi-auto-analysis"
            and _has_upload_context(messages)
            and not _rows_for_followup_chart(last_result)
            and not last_ingestion_rows
        ):
            skill_name = "chatbi-file-ingestion"

        assistant_note = json.dumps(
            {
                "action": "call_skill",
                "skill": skill_name,
                "skill_args": action_model.skill_args or [],
            },
            ensure_ascii=False,
        )
        raw_args = action_model.skill_args or []
        args = skill_args_for_execution(skill_name, raw_args, messages)
        if skill_name == "chatbi-auto-analysis":
            args = _auto_analysis_args(
                user_text,
                args,
                last_result,
                cached_rows=last_ingestion_rows or None,
                column_labels=last_ingestion_column_labels,
                proposal=latest_proposal,
            )
        if skill_name == "chatbi-chart-recommendation":
            args = _chart_recommendation_args(user_text, args, last_result)
        if _should_stop_repeated_subagent_skill(
            subagent_react=subagent_react,
            skill_name=skill_name,
            args=args,
            last_skill_name=last_skill_name,
            last_result=last_result,
            repeated_skill_count=repeated_skill_count,
            previous_args_signature=last_skill_args_signature,
            previous_signature=last_result_signature,
        ):
            log_event(
                trace_id,
                "agent.runner",
                "repeated_skill_converged",
                payload={
                    "mode": "react_subagent",
                    "skill": skill_name,
                    "agent_id": specialist_agent_id,
                    "repeat_count": repeated_skill_count + 1,
                },
            )
            yield {
                "type": "thinking",
                "content": "连续查询未获得新增信息，已基于当前结果交回路由层。",
            }
            merged = _finish_merged(
                result_sink, plan, last_skill_name, last_result, local_executions
            )
            async for event in stream_result_events(last_skill_name or skill_name, plan, merged):
                yield event
            sync_skill_sink(result_sink, last_result, last_skill_name)
            yield {"type": "done", "content": None}
            return
        if _should_short_circuit_repeated_file_ingestion(
            skill_name,
            args,
            last_skill_name,
            last_result,
            messages,
        ):
            yield {
                "type": "thinking",
                "content": "文件已解析完成，正在整理结果...",
            }
            merged = _finish_merged(
                result_sink, plan, last_skill_name, last_result, local_executions
            )
            async for event in stream_result_events(last_skill_name or skill_name, plan, merged):
                yield event
            log_event(
                trace_id,
                "agent.runner",
                "completed",
                payload={"mode": "react", "short_circuit": "repeated_file_ingestion"},
            )
            sync_skill_sink(result_sink, last_result, last_skill_name)
            yield {"type": "done", "content": None}
            return
        execution_action = HarnessAction(
            action="call_skill",
            skill=skill_name,
            skill_args=args,
            text=action_model.text,
            thought=action_model.thought,
            raw_plan=action_model.raw_plan,
        )
        policy = authorize_action(
            execution_action,
            harness_state,
            sorted(allowed_slugs),
            messages=messages,
            specialist_agent_id=specialist_agent_id if subagent_react else None,
            preferred_skills=preferred_skill_slugs,
        )
        if not policy.ok:
            harness_state.record_rejection(policy.reason)
            log_harness_rejected(
                trace_id,
                harness_state,
                category="policy_rejected",
                reason=policy.reason,
                action=execution_action,
            )
            working.append({"role": "assistant", "content": assistant_note})
            working.append(
                {
                    "role": "user",
                    "content": OBS_HEADER + rejection_observation(validation, policy),
                }
            )
            forced_text = _force_subagent_converge_on_policy_reject(
                policy,
                trace_id=trace_id,
                specialist_agent_id=specialist_agent_id if subagent_react else None,
                result_sink=result_sink,
                last_result=last_result,
                last_skill_name=last_skill_name,
            )
            if forced_text:
                yield {"type": "thinking", "content": "前置审计未通过，已收敛为改派建议。"}
                yield {"type": "text", "content": forced_text}
                return
            if harness_state.should_stop_after_rejection():
                break
            yield {"type": "thinking", "content": "正在重新选择更合适的处理方式..."}
            continue
        harness_state.record_accept()
        log_harness_authorized(trace_id, harness_state, execution_action)
        skill_doc = find_skill(skills, skill_name)
        if not skill_doc or (subagent_react and skill_name not in allowed_slugs):
            available = ", ".join(sorted(allowed_slugs)) if allowed_slugs else "（无）"
            obs = json.dumps(
                {
                    "skill_not_in_line": True,
                    "requested": skill_name,
                    "available": sorted(allowed_slugs),
                    "hint": f"请从本专线可用技能中选择：{available}",
                },
                ensure_ascii=False,
            )
            working.append({"role": "assistant", "content": assistant_note})
            working.append({"role": "user", "content": OBS_HEADER + obs})
            yield {
                "type": "thinking",
                "content": f"技能「{skill_name}」不在本专线，请从可用列表重选...",
            }
            continue

        yield {"type": "thinking", "content": f"正在执行 Skill「{skill_name}」..."}
        assistant_note = json.dumps(
            {"action": "call_skill", "skill": skill_name, "skill_args": args},
            ensure_ascii=False,
        )
        log_harness_executing(trace_id, harness_state, execution_action, args)
        try:
            log_event(
                trace_id,
                "agent.skill",
                "started",
                payload=_skill_log_payload(
                    skill_name,
                    skill_doc,
                    agent_id=specialist_agent_id,
                    extra={"args": args},
                ),
            )
            result = run_script(
                skill_doc,
                args,
                trace_id=trace_id,
                skill_db_overrides=skill_db_overrides,
            )
            if skill_name == "chatbi-file-ingestion":
                cached_path = _file_ingestion_result_path(result)
                if cached_path:
                    cache_file_data(cached_path, result)
            log_event(
                trace_id,
                "agent.skill",
                "completed",
                payload=_skill_log_payload(
                    skill_name,
                    skill_doc,
                    agent_id=specialist_agent_id,
                    extra=skill_result_log_payload(result),
                ),
            )
            previous_skill_name = last_skill_name
            last_skill_name = skill_name
            last_result = result
            harness_state.record_skill(skill_name, result)
            called_skills.append(skill_name)
            current_signature = _result_signature(result)
            repeated_skill_count = (
                repeated_skill_count + 1
                if skill_name == previous_skill_name and current_signature == last_result_signature
                else 1
            )
            last_result_signature = current_signature
            last_skill_args_signature = _args_signature(args)
            record_skill_execution(result_sink, skill_name, result, step + 1)
            if result_sink is None:
                local_executions.append(
                    {
                        "skill": skill_name,
                        "result": result,
                        "observation": summarize_observation(skill_name, result),
                        "step": step + 1,
                    }
                )
            else:
                local_executions = get_skill_executions(result_sink)
            if skill_name == "chatbi-file-ingestion":
                ingested = _rows_for_followup_chart(result)
                if ingested:
                    last_ingestion_rows = ingested
                cl = (result.get("data") or {}).get("column_labels")
                if isinstance(cl, dict):
                    last_ingestion_column_labels = cl
                should_continue_auto = (
                    latest_proposal is not None and _is_confirmation_request(user_text)
                ) or (
                    latest_proposal is None
                    and _is_auto_analysis_request(user_text)
                    and not _is_confirmation_request(user_text)
                )
                if should_continue_auto and last_ingestion_rows:
                    auto_doc = find_skill(skills, "chatbi-auto-analysis")
                    if auto_doc:
                        if latest_proposal and _is_confirmation_request(user_text):
                            progress_text = "已恢复上传文件数据，继续执行采纳指标分析..."
                        else:
                            progress_text = "已读取上传文件，继续生成结构化分析建议..."
                        yield {
                            "type": "thinking",
                            "content": progress_text,
                        }
                        skill_name = "chatbi-auto-analysis"
                        auto_args = _auto_analysis_args(
                            user_text,
                            [],
                            result,
                            cached_rows=last_ingestion_rows or None,
                            column_labels=last_ingestion_column_labels,
                            proposal=latest_proposal,
                        )
                        log_event(
                            trace_id,
                            "agent.skill",
                            "started",
                            payload=_skill_log_payload(
                                skill_name,
                                auto_doc,
                                agent_id=specialist_agent_id,
                                extra={
                                    "args": auto_args,
                                    "resumed_after_ingestion": latest_proposal is not None,
                                    "continued_after_ingestion": latest_proposal is None,
                                },
                            ),
                        )
                        result = run_script(
                            auto_doc,
                            auto_args,
                            trace_id=trace_id,
                            skill_db_overrides=skill_db_overrides,
                        )
                        log_event(
                            trace_id,
                            "agent.skill",
                            "completed",
                            payload=_skill_log_payload(
                                skill_name,
                                auto_doc,
                                agent_id=specialist_agent_id,
                                extra=skill_result_log_payload(result),
                            ),
                        )
                        last_skill_name = skill_name
                        last_result = result
                        harness_state.record_skill(skill_name, result)
                        called_skills.append(skill_name)
                        record_skill_execution(result_sink, skill_name, result, step + 1)
                        if result_sink is None:
                            local_executions.append(
                                {
                                    "skill": skill_name,
                                    "result": result,
                                    "observation": summarize_observation(skill_name, result),
                                    "step": step + 1,
                                }
                            )
                        else:
                            local_executions = get_skill_executions(result_sink)
            if _is_terminal_auto_analysis_result(skill_name, result):
                log_harness_observation(
                    trace_id,
                    harness_state,
                    skill_name=skill_name,
                    ok=True,
                    result_kind=str(result.get("kind") or ""),
                    extras=_harness_observation_extras(result),
                )
                audit = _decision_audit_from_extras(_harness_observation_extras(result))
                if audit:
                    log_harness_decision_content_audit(
                        trace_id,
                        harness_state,
                        skill_name=skill_name,
                        audit=audit,
                        agent_id=specialist_agent_id,
                    )
                yield {
                    "type": "thinking",
                    "content": "自动分析已生成结构化结果，正在展示...",
                }
                merged = _finish_merged(
                    result_sink, plan, last_skill_name, last_result, local_executions
                )
                async for event in stream_result_events(skill_name, plan, merged):
                    yield event
                log_event(
                    trace_id,
                    "agent.runner",
                    "completed",
                    payload={"mode": "react", "short_circuit": "auto_analysis"},
                )
                sync_skill_sink(result_sink, last_result, last_skill_name)
                yield {"type": "done", "content": None}
                return
            obs = summarize_observation(skill_name, result)
            extras = _harness_observation_extras(result)
            log_harness_observation(
                trace_id,
                harness_state,
                skill_name=skill_name,
                ok=True,
                result_kind=str(result.get("kind") or ""),
                extras=extras,
            )
            audit = _decision_audit_from_extras(extras)
            if audit:
                log_harness_decision_content_audit(
                    trace_id,
                    harness_state,
                    skill_name=skill_name,
                    audit=audit,
                    agent_id=specialist_agent_id,
                )
        except Exception as exc:
            log_event(
                trace_id,
                "agent.skill",
                "failed",
                str(exc),
                {"skill": skill_name},
                "ERROR",
            )
            obs = json.dumps(
                {"skill": skill_name, "ok": False, "error": str(exc)},
                ensure_ascii=False,
            )
            log_harness_observation(
                trace_id,
                harness_state,
                skill_name=skill_name,
                ok=False,
                error=str(exc),
            )

        working.append({"role": "assistant", "content": assistant_note})
        working.append({"role": "user", "content": OBS_HEADER + obs})
        yield {"type": "thinking", "content": "已收到 Observation，继续推理..."}

        if (
            skill_name == "chatbi-semantic-query"
            and is_query_plus_decision_text(user_text)
            and "chatbi-decision-advisor" not in called_skills
        ):
            advice_doc = find_skill(skills, "chatbi-decision-advisor")
            if advice_doc:
                try:
                    followup_events, advice_result, followup_messages = run_decision_followup(
                        advice_doc,
                        messages,
                        user_text,
                        trace_id,
                        skill_db_overrides,
                    )
                    for event in followup_events:
                        yield event
                    last_skill_name = "chatbi-decision-advisor"
                    last_result = advice_result
                    harness_state.record_skill("chatbi-decision-advisor", advice_result)
                    called_skills.append("chatbi-decision-advisor")
                    record_skill_execution(
                        result_sink,
                        "chatbi-decision-advisor",
                        advice_result,
                        step + 1,
                    )
                    if result_sink is None:
                        local_executions.append(
                            {
                                "skill": "chatbi-decision-advisor",
                                "result": advice_result,
                                "observation": summarize_observation(
                                    "chatbi-decision-advisor", advice_result
                                ),
                                "step": step + 1,
                            }
                        )
                    else:
                        local_executions = get_skill_executions(result_sink)
                    working.extend(followup_messages)
                except Exception as exc:
                    yield {"type": "error", "content": f"决策建议执行失败：{exc}"}
                    yield {"type": "done", "content": None}
                    return

    if last_result:
        yield {
            "type": "thinking",
            "content": "已达到最大推理步数，展示最后一次工具结果。",
        }
        fallback_plan: Dict[str, Any] = {
            "chart_plan": None,
            "kpi_cards": None,
            "text": "已达到最大推理步数，以上为最后一次工具返回的数据摘要。",
        }

        """
        Merge llm last output and last skill output.

        For example:
            call_skill → chatbi-semantic-query → skill result = {"text": "本月销售额 100 万", "chart_plan": {...}}
            LLM result= action="finish", plan={"text": "以下是您要求的数据..."}

            final result: skill result(chart/kpis/text) + llm result(text)
        """
        merged = _finish_merged(
            result_sink, fallback_plan, last_skill_name, last_result, local_executions
        )
        """
        stream_result_events:
        transfer the skill result to the frontend page by sse.
        """
        async for event in stream_result_events(last_skill_name or "skill", fallback_plan, merged):
            yield event
    else:
        yield {
            "type": "text",
            "content": "已达到最大推理步数，尚未获得工具结果。请简化问题或稍后重试。",
        }
    log_event(
        trace_id,
        "agent.runner",
        "completed",
        payload={"mode": "react", "exhausted": True},
    )
    sync_skill_sink(result_sink, last_result, last_skill_name)
    yield {"type": "done", "content": None}
