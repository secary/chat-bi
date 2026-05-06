from __future__ import annotations

from typing import Any, AsyncGenerator, Dict, List

from backend.agent.executor import find_skill, run_script, skill_args_for_execution
from backend.agent.formatter import stream_result_events
from backend.agent.planner import call_llm_for_plan
from backend.agent.prompt_builder import build_system_prompt, scan_skills
from backend.agent.react_runner import stream_chat_react
from backend.config import settings
from backend.trace import log_event


async def stream_chat(
    messages: List[Dict[str, str]],
    trace_id: str = "",
) -> AsyncGenerator[Dict[str, Any], None]:
    """Agent loop: ReAct multi-step (default) or legacy single plan + one Skill."""
    if settings.agent_react:
        async for event in stream_chat_react(messages, trace_id=trace_id):
            yield event
        return

    async for event in _stream_chat_legacy(messages, trace_id=trace_id):
        yield event


async def _stream_chat_legacy(
    messages: List[Dict[str, str]],
    trace_id: str = "",
) -> AsyncGenerator[Dict[str, Any], None]:
    """Single LLM JSON plan and at most one Skill execution."""
    log_event(
        trace_id,
        "agent.runner",
        "started",
        payload={"message_count": len(messages), "mode": "legacy"},
    )
    skills = scan_skills(settings.skills_dir)
    system_prompt = build_system_prompt(skills)

    yield {"type": "thinking", "content": "正在分析您的问题，理解业务语义..."}
    log_event(
        trace_id, "agent.planner", "started", payload={"skill_count": len(skills)}
    )
    plan = await call_llm_for_plan(system_prompt, messages)
    log_event(
        trace_id,
        "agent.planner",
        "completed",
        payload={"skill": plan.get("skill") if plan else None},
    )

    if not plan or not plan.get("skill"):
        log_event(trace_id, "agent.runner", "no_skill")
        yield {"type": "thinking", "content": "正在整理回答..."}
        if plan and plan.get("text"):
            yield {"type": "text", "content": plan["text"]}
        yield {"type": "done", "content": None}
        return

    skill_name = plan["skill"]
    skill_doc = find_skill(skills, skill_name)
    if not skill_doc:
        log_event(
            trace_id,
            "agent.runner",
            "skill_missing",
            f"未找到技能：{skill_name}",
            level="ERROR",
        )
        yield {"type": "error", "content": f"未找到技能：{skill_name}"}
        yield {"type": "done", "content": None}
        return

    yield {"type": "thinking", "content": f"已选择技能「{skill_name}」"}
    yield {"type": "thinking", "content": f"正在执行 {skill_name}..."}

    try:
        args = skill_args_for_execution(
            skill_name, plan.get("skill_args", []), messages
        )
        log_event(
            trace_id,
            "agent.skill",
            "started",
            payload={"skill": skill_name, "args": args},
        )
        result = run_script(skill_doc, args, trace_id=trace_id)
        log_event(
            trace_id,
            "agent.skill",
            "completed",
            payload={"skill": skill_name, "kind": result.get("kind")},
        )
    except Exception as exc:
        log_event(
            trace_id, "agent.skill", "failed", str(exc), {"skill": skill_name}, "ERROR"
        )
        yield {"type": "error", "content": f"脚本执行失败：{exc}"}
        yield {"type": "done", "content": None}
        return

    yield {"type": "thinking", "content": "正在整理查询结果..."}
    async for event in stream_result_events(skill_name, plan, result):
        yield event
    log_event(trace_id, "agent.runner", "completed", payload={"mode": "legacy"})
    yield {"type": "done", "content": None}
