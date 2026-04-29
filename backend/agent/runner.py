from __future__ import annotations

from typing import Any, AsyncGenerator, Dict, List

from backend.agent.executor import find_skill, run_script, skill_args_for_execution
from backend.agent.formatter import stream_result_events
from backend.agent.planner import call_llm_for_plan
from backend.agent.prompt_builder import build_system_prompt, scan_skills
from backend.config import settings


async def stream_chat(
    messages: List[Dict[str, str]],
) -> AsyncGenerator[Dict[str, Any], None]:
    """Agent loop: plan, execute one Skill, stream normalized result events."""
    skills = scan_skills(settings.skills_dir)
    system_prompt = build_system_prompt(skills)

    yield {"type": "thinking", "content": "正在分析您的问题，理解业务语义..."}
    plan = await call_llm_for_plan(system_prompt, messages)

    if not plan or not plan.get("skill"):
        yield {"type": "thinking", "content": "正在整理回答..."}
        if plan and plan.get("text"):
            yield {"type": "text", "content": plan["text"]}
        yield {"type": "done", "content": None}
        return

    skill_name = plan["skill"]
    skill_doc = find_skill(skills, skill_name)
    if not skill_doc:
        yield {"type": "error", "content": f"未找到技能：{skill_name}"}
        yield {"type": "done", "content": None}
        return

    yield {"type": "thinking", "content": f"已选择技能「{skill_name}」"}
    yield {"type": "thinking", "content": f"正在执行 {skill_name}..."}

    try:
        args = skill_args_for_execution(skill_name, plan.get("skill_args", []), messages)
        result = run_script(skill_doc, args)
    except Exception as exc:
        yield {"type": "error", "content": f"脚本执行失败：{exc}"}
        yield {"type": "done", "content": None}
        return

    yield {"type": "thinking", "content": "正在整理查询结果..."}
    async for event in stream_result_events(skill_name, plan, result):
        yield event
    yield {"type": "done", "content": None}
