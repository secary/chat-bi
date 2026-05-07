from __future__ import annotations

import json
from typing import Any, AsyncGenerator, Dict, List, Optional

from backend.agent.executor import (
    find_skill,
    run_script,
    skill_result_log_payload,
    skill_args_for_execution,
)
from backend.agent.formatter import stream_result_events
from backend.agent.observation import summarize_observation
from backend.agent.planner import call_llm_for_react_step
from backend.agent.prompt_builder import build_react_system_prompt, scan_skills_enabled
from backend.config import settings
from backend.trace import log_event

OBS_HEADER = "以下为工具执行后的 Observation（JSON 摘要），请基于事实继续推理：\n"


def _merge_finish_result(
    plan: Dict[str, Any], last_result: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    merged: Dict[str, Any] = dict(last_result or {})
    if plan.get("text"):
        merged["text"] = plan["text"]
    return merged


async def stream_chat_react(
    messages: List[Dict[str, str]],
    trace_id: str = "",
    skill_db_overrides: Optional[Dict[str, str]] = None,
    memory_block: Optional[str] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    log_event(
        trace_id,
        "agent.runner",
        "started",
        payload={"message_count": len(messages), "mode": "react"},
    )
    skills = scan_skills_enabled(settings.skills_dir)
    system_prompt = build_react_system_prompt(skills)
    if memory_block and memory_block.strip():
        system_prompt = memory_block.strip() + "\n\n" + system_prompt

    working = [dict(m) for m in messages]
    last_skill_name: Optional[str] = None
    last_result: Optional[Dict[str, Any]] = None

    yield {"type": "thinking", "content": "正在分析您的问题（ReAct 多步推理）..."}

    for step in range(settings.agent_max_steps):
        log_event(
            trace_id,
            "agent.planner",
            "react.step",
            payload={"step": step + 1, "max_steps": settings.agent_max_steps},
        )
        plan = await call_llm_for_react_step(system_prompt, working)
        if not plan:
            yield {"type": "error", "content": "模型未返回有效 JSON。"}
            yield {"type": "done", "content": None}
            return

        thought = plan.get("thought")
        if isinstance(thought, str) and thought.strip():
            yield {"type": "thinking", "content": thought.strip()}

        action = str(plan.get("action") or "finish").strip().lower()
        if action in ("finish", "done", "answer"):
            yield {"type": "thinking", "content": "正在整理回答..."}
            merged = _merge_finish_result(plan, last_result)
            skill_label = last_skill_name or "chatbi-semantic-query"
            async for event in stream_result_events(skill_label, plan, merged):
                yield event
            log_event(
                trace_id,
                "agent.runner",
                "completed",
                payload={"mode": "react", "steps": step + 1},
            )
            yield {"type": "done", "content": None}
            return

        if action != "call_skill":
            yield {
                "type": "error",
                "content": f"无法识别的 action：{plan.get('action')}",
            }
            yield {"type": "done", "content": None}
            return

        skill_name = plan.get("skill")
        if not skill_name or not isinstance(skill_name, str):
            yield {"type": "error", "content": "call_skill 缺少有效的 skill 名称。"}
            yield {"type": "done", "content": None}
            return

        skill_doc = find_skill(skills, skill_name)
        if not skill_doc:
            yield {"type": "error", "content": f"未找到技能：{skill_name}"}
            yield {"type": "done", "content": None}
            return

        yield {"type": "thinking", "content": f"正在执行 Skill「{skill_name}」..."}

        args = skill_args_for_execution(
            skill_name, plan.get("skill_args") or [], messages
        )
        assistant_note = json.dumps(
            {"action": "call_skill", "skill": skill_name, "skill_args": args},
            ensure_ascii=False,
        )

        try:
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
                payload={"skill": skill_name, **skill_result_log_payload(result)},
            )
            last_skill_name = skill_name
            last_result = result
            obs = summarize_observation(skill_name, result)
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

        working.append({"role": "assistant", "content": assistant_note})
        working.append({"role": "user", "content": OBS_HEADER + obs})
        yield {"type": "thinking", "content": "已收到 Observation，继续推理..."}

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
        merged = _merge_finish_result(fallback_plan, last_result)
        async for event in stream_result_events(
            last_skill_name or "skill", fallback_plan, merged
        ):
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
    yield {"type": "done", "content": None}
