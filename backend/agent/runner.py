from __future__ import annotations

from typing import Any, AsyncGenerator, Dict, List, Optional

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
from backend.config import settings
from backend.trace import log_event


def _legacy_sink_write(
    sink: Optional[Dict[str, Any]],
    last_result: Optional[Dict[str, Any]],
    last_skill_name: Optional[str],
) -> None:
    if sink is None:
        return
    sink["last_result"] = last_result
    sink["last_skill_name"] = last_skill_name


def _is_query_plus_decision(messages: List[Dict[str, str]]) -> bool:
    return is_query_plus_decision_text(latest_user_content(messages))


def _infer_primary_dimension(result: Dict[str, Any]) -> str:
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


async def stream_chat(
    messages: List[Dict[str, str]],
    trace_id: str = "",
    skill_db_overrides: Optional[Dict[str, str]] = None,
    memory_block: Optional[str] = None,
    multi_agents: bool = False,
    session_id: Optional[int] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """Agent loop: ReAct multi-step or legacy single-plan Skill execution."""
    if multi_agents:
        from backend.agent.multi_agent_runner import stream_chat_multi_agent

        async for event in stream_chat_multi_agent(
            messages,
            trace_id=trace_id,
            skill_db_overrides=skill_db_overrides,
            memory_block=memory_block,
            session_id=session_id,
        ):
            yield event
        return

    if settings.agent_react:
        async for event in stream_chat_react(
            messages,
            trace_id=trace_id,
            skill_db_overrides=skill_db_overrides,
            memory_block=memory_block,
            session_id=session_id,
        ):
            yield event
        return

    async for event in _stream_chat_legacy(
        messages,
        trace_id=trace_id,
        skill_db_overrides=skill_db_overrides,
        memory_block=memory_block,
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
    """Single LLM JSON plan with optional two-step query and advice execution."""
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
        yield {"type": "thinking", "content": "识别为简单话语，直接回复。"}
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
    role_prompt: Optional[str] = None,
    trace_id: str = "",
    skill_db_overrides: Optional[Dict[str, str]] = None,
    memory_block: Optional[str] = None,
    result_sink: Optional[Dict[str, Any]] = None,
    subagent_mode: bool = False,
    specialist_agent_id: Optional[str] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """One specialist pass: ReAct or Legacy with a filtered skill list."""
    if settings.agent_react:
        async for event in stream_chat_react(
            messages,
            trace_id=trace_id,
            skill_db_overrides=skill_db_overrides,
            memory_block=memory_block,
            skill_docs=skill_docs,
            role_prompt=role_prompt,
            result_sink=result_sink,
            subagent_react=subagent_mode,
            specialist_agent_id=specialist_agent_id,
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
