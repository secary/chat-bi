from __future__ import annotations

from typing import Any, AsyncGenerator, Dict, List, Optional, Union

from backend.agent.execution_audit import (
    RemediationAction,
    audit_single_result_for_remediation,
    chart_recommendation_args,
)
from backend.agent.execution_decider import ExecutionDecision, decide_execution_mode
from backend.agent.executor import (
    find_skill,
    latest_user_content,
    run_script,
    skill_result_log_payload,
    skill_args_for_execution,
)
from backend.agent.formatter import stream_result_events
from backend.agent.intent_guard import small_talk_reply, should_skip_skill_for_message
from backend.agent.abort_async import ChatAbortedError
from backend.agent.planner import call_llm_for_plan
from backend.agent.prompt_builder import (
    SkillDoc,
    build_system_prompt,
    scan_skills_enabled,
)
from backend.agent.prompt_subagent import build_system_prompt_for_subagent
from backend.agent.query_decision import is_query_plus_decision_text
from backend.agent.react_runner import stream_chat_react
from backend.agent.react_followup import run_decision_followup
from backend.config import settings
from backend.trace import log_event


def _legacy_sink_write(
    sink: Optional[Dict[str, Any]],
    last_result: Optional[Dict[str, Any]],
    last_skill_name: Optional[str],
) -> None:
    """Writes the last executed result and skill name into the result sink dict."""
    if sink is None:
        return
    sink["last_result"] = last_result
    sink["last_skill_name"] = last_skill_name


def _is_query_plus_decision(messages: List[Dict[str, str]]) -> bool:
    """Returns True if the user's message contains both a query and a decision intent."""
    return is_query_plus_decision_text(latest_user_content(messages))


def _infer_primary_dimension(result: Dict[str, Any]) -> str:
    """Infers the primary dimension column name from a query result (first column of the first row)."""
    data = result.get("data", {})
    rows = data.get("rows") if isinstance(data, dict) else None
    if not isinstance(rows, list) or not rows or not isinstance(rows[0], dict):
        return ""
    keys = list(rows[0].keys())
    return keys[0] if len(keys) > 1 else ""


def _build_steps(
    plan: Dict[str, Any],
    messages: List[Dict[str, str]],
) -> List[Dict[str, Any]]:
    """
    Builds an ordered list of execution steps from an LLM plan.
    If the message has both query and decision intent, returns two steps:
      1. chatbi-semantic-query  (the data query)
      2. chatbi-decision-advisor (advice based on the query result)
    Otherwise returns a single step for the planned skill.
    """
    user_text = latest_user_content(messages)
    if _is_query_plus_decision(messages):
        query_plan = plan if plan.get("skill") == "chatbi-semantic-query" else {}
        return [
            {
                "skill": "chatbi-semantic-query",
                "skill_args": [user_text],
                "plan": query_plan,
                "phase": "查询",
            },
            {
                "skill": "chatbi-decision-advisor",
                "skill_args": [user_text],
                "plan": {},
                "phase": "建议",
            },
        ]
    return [
        {
            "skill": plan["skill"],
            "skill_args": plan.get("skill_args", []),
            "plan": plan,
            "phase": "查询",
        }
    ]


"""
The agent main entrance.
if multi-agents mode is on, then goes to stream_chat_multi_agent
otherwise, it goes to stream_chat_react. React(think-do-observe) mode.
stream_chat_legacy is not in use by default. It is not ReAct mode.
"""


def _clarification_text(decision: ExecutionDecision) -> str:
    flags = set(decision.risk_flags)
    if "empty_message" in flags:
        return "请先输入你想分析的问题，例如“查华东近3个月销售额”或“基于华东近3个月销售和毛利给经营建议”。"
    if "decision_without_facts" in flags or decision.route_sequence == ["business_advisor"]:
        return "我可以给经营建议，但需要先有明确事实范围。请补充要分析的指标、时间或区域，例如“基于华东近3个月销售和毛利给经营建议”。"
    return decision.reason or "我还需要更多信息才能继续，请补充要分析的指标、时间、区域或数据范围。"


async def _stream_ask_for_clarification(
    decision: ExecutionDecision,
    trace_id: str = "",
) -> AsyncGenerator[Dict[str, Any], None]:
    log_event(
        trace_id,
        "agent.harness",
        "execution_decision_ask",
        payload={
            "mode": decision.mode,
            "reason": decision.reason,
            "route_sequence": decision.route_sequence,
            "confidence": decision.confidence,
            "risk_flags": decision.risk_flags,
        },
    )
    yield {"type": "thinking", "content": "正在确认最稳妥的处理方式..."}
    yield {"type": "text", "content": _clarification_text(decision)}
    yield {"type": "done", "content": None}


async def _stream_remediation_action(
    action: RemediationAction,
    messages: List[Dict[str, str]],
    last_result: Dict[str, Any],
    trace_id: str,
    skill_db_overrides: Optional[Dict[str, str]],
) -> AsyncGenerator[Dict[str, Any], None]:
    skills = scan_skills_enabled(settings.skills_dir)
    skill_doc = find_skill(skills, action.skill)
    if not skill_doc:
        log_event(
            trace_id,
            "agent.harness",
            "post_audit_remediation_skipped",
            payload={"skill": action.skill, "reason": "skill_missing"},
            level="WARN",
        )
        return

    user_text = latest_user_content(messages)
    log_event(
        trace_id,
        "agent.harness",
        "post_audit_remediation_started",
        payload={"skill": action.skill, "reason": action.reason},
    )
    yield {"type": "thinking", "content": f"后审计发现输出不完整，正在补充：{action.reason}"}

    if action.skill == "chatbi-decision-advisor":
        followup_events, result, _ = run_decision_followup(
            skill_doc,
            messages,
            user_text,
            trace_id,
            skill_db_overrides,
        )
        for event in followup_events:
            yield event
    elif action.skill == "chatbi-chart-recommendation":
        args = chart_recommendation_args(user_text, last_result)
        log_event(
            trace_id,
            "agent.skill",
            "started",
            payload={"skill": action.skill, "args": args, "agent_id": "post_audit"},
        )
        result = run_script(
            skill_doc,
            args,
            trace_id=trace_id,
            skill_db_overrides=skill_db_overrides,
        )
        log_event(
            trace_id,
            "agent.skill",
            "completed",
            payload={
                "skill": action.skill,
                "agent_id": "post_audit",
                **skill_result_log_payload(result),
            },
        )
    else:
        return

    async for event in stream_result_events(action.skill, {}, result):
        yield event
    log_event(
        trace_id,
        "agent.harness",
        "post_audit_remediation_completed",
        payload={"skill": action.skill},
    )


async def _stream_single_with_post_audit(
    messages: List[Dict[str, str]],
    trace_id: str,
    skill_db_overrides: Optional[Dict[str, str]],
    memory_block: Optional[str],
    session_id: Optional[int],
) -> AsyncGenerator[Dict[str, Any], None]:
    result_sink: Dict[str, Any] = {}
    emitted_types: List[str] = []
    pending_done: Optional[Dict[str, Any]] = None

    source = (
        stream_chat_react(
            messages,
            trace_id=trace_id,
            skill_db_overrides=skill_db_overrides,
            memory_block=memory_block,
            result_sink=result_sink,
            session_id=session_id,
        )
        if settings.agent_react
        else _stream_chat_legacy(
            messages,
            trace_id=trace_id,
            skill_db_overrides=skill_db_overrides,
            memory_block=memory_block,
            result_sink=result_sink,
        )
    )
    async for event in source:
        event_type = str(event.get("type") or "")
        if event_type == "done":
            pending_done = event
            continue
        if event_type:
            emitted_types.append(event_type)
        yield event

    last_result = result_sink.get("last_result")
    last_skill_name = result_sink.get("last_skill_name")
    actions = audit_single_result_for_remediation(
        messages,
        last_result if isinstance(last_result, dict) else None,
        last_skill_name if isinstance(last_skill_name, str) else None,
        emitted_types,
    )
    if actions:
        log_event(
            trace_id,
            "agent.harness",
            "post_audit_remediation_selected",
            payload={
                "skills": [action.skill for action in actions],
                "reasons": [action.reason for action in actions],
            },
        )
    for action in actions:
        if not isinstance(last_result, dict):
            break
        async for event in _stream_remediation_action(
            action,
            messages,
            last_result,
            trace_id,
            skill_db_overrides,
        ):
            yield event

    yield pending_done or {"type": "done", "content": None}


async def stream_chat(
    messages: List[Dict[str, str]],
    trace_id: str = "",
    skill_db_overrides: Optional[Dict[str, str]] = None,
    memory_block: Optional[str] = None,
    multi_agents: Union[bool, str] = "auto",
    session_id: Optional[int] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """Agent entry point: routes to multi-agent, ReAct, or legacy execution mode."""
    force_multi = multi_agents is True
    force_single = multi_agents is False or (
        isinstance(multi_agents, str) and multi_agents == "single"
    )
    decision: Optional[ExecutionDecision] = None
    if not force_multi and not force_single:
        decision = decide_execution_mode(messages)
        log_event(
            trace_id,
            "agent.harness",
            "execution_decision_selected",
            payload={
                "mode": decision.mode,
                "reason": decision.reason,
                "route_sequence": decision.route_sequence,
                "confidence": decision.confidence,
                "risk_flags": decision.risk_flags,
            },
        )
        if decision.mode == "ask":
            async for event in _stream_ask_for_clarification(decision, trace_id=trace_id):
                yield event
            return
        force_multi = decision.mode == "multi"

    if force_multi:
        from backend.agent.multi_agent_runner import stream_chat_multi_agent

        async for event in stream_chat_multi_agent(
            messages,
            trace_id=trace_id,
            skill_db_overrides=skill_db_overrides,
            memory_block=memory_block,
            session_id=session_id,
            controlled_intent=decision.intent if decision else None,
        ):
            yield event
        return

    async for event in _stream_single_with_post_audit(
        messages,
        trace_id=trace_id,
        skill_db_overrides=skill_db_overrides,
        memory_block=memory_block,
        session_id=session_id,
    ):
        yield event


async def _stream_chat_legacy(
    messages: List[Dict[str, str]],
    trace_id: str = "",
    skill_db_overrides: Optional[Dict[str, str]] = None,
    memory_block: Optional[str] = None,
    skill_docs: Optional[List[SkillDoc]] = None,
    role_prompt: Optional[str] = None,
    result_sink: Optional[Dict[str, Any]] = None,
    subagent_mode: bool = False,
    specialist_agent_id: Optional[str] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Legacy single-shot mode: one LLM call produces a JSON plan, then executes
    one or two skills (query + optional decision advice) based on user intent.
    """
    log_event(
        trace_id,
        "agent.runner",
        "started",
        payload={"message_count": len(messages), "mode": "legacy"},
    )
    skills = skill_docs if skill_docs is not None else scan_skills_enabled(settings.skills_dir)
    user_text = latest_user_content(messages)
    if should_skip_skill_for_message(user_text):
        log_event(trace_id, "agent.runner", "skip_skill_small_talk")
        _legacy_sink_write(result_sink, None, None)
        yield {"type": "thinking", "content": "正在准备回复..."}
        yield {"type": "text", "content": small_talk_reply(user_text)}
        yield {"type": "done", "content": None}
        return
    system_prompt = (
        build_system_prompt_for_subagent(skills) if subagent_mode else build_system_prompt(skills)
    )
    if role_prompt and role_prompt.strip():
        system_prompt = role_prompt.strip() + "\n\n" + system_prompt
    if memory_block and memory_block.strip():
        system_prompt = memory_block.strip() + "\n\n" + system_prompt

    yield {"type": "thinking", "content": "正在分析您的问题，理解业务语义..."}
    log_event(trace_id, "agent.planner", "started", payload={"skill_count": len(skills)})
    try:
        plan = await call_llm_for_plan(system_prompt, messages, trace_id=trace_id)
    except ChatAbortedError:
        log_event(trace_id, "agent.runner", "aborted", level="INFO")
        _legacy_sink_write(result_sink, None, None)
        yield {"type": "thinking", "content": "用户中止了查询。"}
        yield {"type": "done", "content": None}
        return
    log_event(
        trace_id,
        "agent.planner",
        "completed",
        payload={"skill": plan.get("skill") if plan else None},
    )

    if not plan or not plan.get("skill"):
        log_event(trace_id, "agent.runner", "no_skill")
        _legacy_sink_write(result_sink, None, None)
        yield {"type": "thinking", "content": "正在整理回答..."}
        if plan and plan.get("text"):
            yield {"type": "text", "content": plan["text"]}
        yield {"type": "done", "content": None}
        return

    steps = _build_steps(plan, messages)
    if len(steps) > 1:
        yield {
            "type": "thinking",
            "content": "识别到您同时需要查询结果和经营建议，开始分两步处理。",
        }

    previous_result: Dict[str, Any] | None = None
    last_skill_executed: Optional[str] = None
    for step in steps:
        skill_name = step["skill"]
        skill_doc = find_skill(skills, skill_name)
        if not skill_doc:
            log_event(
                trace_id,
                "agent.runner",
                "skill_missing",
                f"未找到技能：{skill_name}",
                level="ERROR",
            )
            _legacy_sink_write(result_sink, previous_result, last_skill_executed)
            yield {"type": "error", "content": f"未找到技能：{skill_name}"}
            yield {"type": "done", "content": None}
            return

        yield {"type": "thinking", "content": f"已选择技能「{skill_name}」"}
        if step["phase"] == "建议":
            yield {"type": "thinking", "content": "正在基于当前问题生成经营决策建议..."}
        else:
            yield {"type": "thinking", "content": f"正在执行 {skill_name}..."}

        try:
            args = skill_args_for_execution(skill_name, step["skill_args"], messages)
            if skill_name == "chatbi-decision-advisor" and previous_result:
                dimension = _infer_primary_dimension(previous_result)
                if dimension and args:
                    args = [f"{args[0]}，重点分析维度：{dimension}"]
            log_event(
                trace_id,
                "agent.skill",
                "started",
                payload={
                    "skill": skill_name,
                    "args": args,
                    "agent_id": specialist_agent_id or "single",
                },
            )
            result = run_script(
                skill_doc,
                args,
                trace_id=trace_id,
                skill_db_overrides=skill_db_overrides,
            )
            log_event(
                trace_id,
                "agent.skill",
                "completed",
                payload={"skill": skill_name, **skill_result_log_payload(result)},
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
            _legacy_sink_write(result_sink, previous_result, last_skill_executed)
            yield {"type": "error", "content": f"脚本执行失败：{exc}"}
            yield {"type": "done", "content": None}
            return

        summary = "正在整理经营建议..." if step["phase"] == "建议" else "正在整理查询结果..."
        yield {"type": "thinking", "content": summary}
        async for event in stream_result_events(skill_name, step["plan"], result):
            yield event
        previous_result = result
        last_skill_executed = skill_name

    log_event(trace_id, "agent.runner", "completed", payload={"mode": "legacy"})
    _legacy_sink_write(result_sink, previous_result, last_skill_executed)
    yield {"type": "done", "content": None}


async def stream_specialist(
    messages: List[Dict[str, str]],
    skill_docs: List[SkillDoc],
    preferred_skill_slugs: Optional[List[str]] = None,
    role_prompt: Optional[str] = None,
    trace_id: str = "",
    skill_db_overrides: Optional[Dict[str, str]] = None,
    memory_block: Optional[str] = None,
    result_sink: Optional[Dict[str, Any]] = None,
    subagent_mode: bool = False,
    specialist_agent_id: Optional[str] = None,
    initial_last_result: Optional[Dict[str, Any]] = None,
    initial_last_skill_name: Optional[str] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Runs one specialist pass for a single agent in multi-agent mode.
    Uses a pre-filtered skill list instead of all available skills.
    Routes to ReAct or legacy mode based on settings.
    """
    if settings.agent_react:
        async for event in stream_chat_react(
            messages,
            trace_id=trace_id,
            skill_db_overrides=skill_db_overrides,
            memory_block=memory_block,
            skill_docs=skill_docs,
            preferred_skill_slugs=preferred_skill_slugs,
            role_prompt=role_prompt,
            result_sink=result_sink,
            subagent_react=subagent_mode,
            specialist_agent_id=specialist_agent_id,
            initial_last_result=initial_last_result,
            initial_last_skill_name=initial_last_skill_name,
        ):
            yield event
        return
    async for event in _stream_chat_legacy(
        messages,
        trace_id=trace_id,
        skill_db_overrides=skill_db_overrides,
        memory_block=memory_block,
        skill_docs=skill_docs,
        role_prompt=role_prompt,
        result_sink=result_sink,
        subagent_mode=subagent_mode,
        specialist_agent_id=specialist_agent_id,
    ):
        yield event
