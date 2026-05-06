from __future__ import annotations

import re
from typing import Any, AsyncGenerator, Dict, List, Optional

from backend.agent.executor import (
    find_skill,
    latest_user_content,
    run_script,
    skill_args_for_execution,
)
from backend.agent.formatter import stream_result_events
from backend.agent.planner import call_llm_for_plan
from backend.agent.prompt_builder import build_system_prompt, scan_skills_enabled
from backend.agent.react_runner import stream_chat_react
from backend.config import settings
from backend.trace import log_event


_DECISION_RE = re.compile(
    r"(决策建议|决策意见|经营建议|经营意见|管理建议|管理意见|建议|意见)"
)
_QUERY_RE = re.compile(
    r"(排行|排名|对比|趋势|汇总|查询|销售额|毛利|毛利率|目标完成率|留存率|客户数|订单数|"
    r"各区域|按区域|按月|按照.{0,10}划分|按.{0,10}划分|产品|渠道|部门|客户类型)"
)


def _is_query_plus_decision(messages: List[Dict[str, str]]) -> bool:
    text = latest_user_content(messages)
    return bool(text and _QUERY_RE.search(text) and _DECISION_RE.search(text))


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


async def stream_chat(
    messages: List[Dict[str, str]],
    trace_id: str = "",
    skill_db_overrides: Optional[Dict[str, str]] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """Agent loop: ReAct multi-step or legacy single-plan Skill execution."""
    if settings.agent_react:
        async for event in stream_chat_react(
            messages, trace_id=trace_id, skill_db_overrides=skill_db_overrides
        ):
            yield event
        return

    async for event in _stream_chat_legacy(
        messages, trace_id=trace_id, skill_db_overrides=skill_db_overrides
    ):
        yield event


async def _stream_chat_legacy(
    messages: List[Dict[str, str]],
    trace_id: str = "",
    skill_db_overrides: Optional[Dict[str, str]] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """Single LLM JSON plan with optional two-step query and advice execution."""
    log_event(
        trace_id,
        "agent.runner",
        "started",
        payload={"message_count": len(messages), "mode": "legacy"},
    )
    skills = scan_skills_enabled(settings.skills_dir)
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

    steps = _build_steps(plan, messages)
    if len(steps) > 1:
        yield {
            "type": "thinking",
            "content": "识别到您同时需要查询结果和经营建议，开始分两步处理。",
        }

    previous_result: Dict[str, Any] | None = None
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
                payload={"skill": skill_name, "args": args},
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
                payload={"skill": skill_name, "kind": result.get("kind")},
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
            yield {"type": "error", "content": f"脚本执行失败：{exc}"}
            yield {"type": "done", "content": None}
            return

        summary = (
            "正在整理经营建议..."
            if step["phase"] == "建议"
            else "正在整理查询结果..."
        )
        yield {"type": "thinking", "content": summary}
        async for event in stream_result_events(skill_name, step["plan"], result):
            yield event
        previous_result = result

    log_event(trace_id, "agent.runner", "completed", payload={"mode": "legacy"})
    yield {"type": "done", "content": None}
