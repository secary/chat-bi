from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from backend.agent.executor import run_script, skill_args_for_execution, skill_result_log_payload
from backend.agent.observation import summarize_observation
from backend.agent.prompt_builder import SkillDoc
from backend.trace import log_event

OBS_HEADER = "以下为工具执行后的 Observation（JSON 摘要），请基于事实继续推理：\n"


def run_decision_followup(
    skill_doc: SkillDoc,
    messages: List[Dict[str, str]],
    user_text: str,
    trace_id: str,
    skill_db_overrides: Optional[Dict[str, str]] = None,
) -> tuple[list[dict], Dict[str, Any], list[Dict[str, str]]]:
    events = [
        {
            "type": "thinking",
            "content": "检测到查询后还需要经营建议，继续执行 Skill「chatbi-decision-advisor」。",
        }
    ]
    args = skill_args_for_execution("chatbi-decision-advisor", [user_text], messages)
    log_event(
        trace_id,
        "agent.skill",
        "started",
        payload={"skill": "chatbi-decision-advisor", "args": args},
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
        payload={"skill": "chatbi-decision-advisor", **skill_result_log_payload(result)},
    )
    obs = summarize_observation("chatbi-decision-advisor", result)
    working_messages = [
        {
            "role": "assistant",
            "content": json.dumps(
                {
                    "action": "call_skill",
                    "skill": "chatbi-decision-advisor",
                    "skill_args": args,
                },
                ensure_ascii=False,
            ),
        },
        {"role": "user", "content": OBS_HEADER + obs},
    ]
    events.append({"type": "thinking", "content": "已收到决策建议 Observation，继续整理回答..."})
    return events, result, working_messages
