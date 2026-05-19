from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

_ACTION_ALIASES = {
    "answer": "finish",
    "ask": "ask_clarification",
    "ask_clarification": "ask_clarification",
    "call_skill": "call_skill",
    "done": "finish",
    "finish": "finish",
}


@dataclass(frozen=True)
class HarnessAction:
    action: str
    skill: Optional[str] = None
    skill_args: Optional[List[str]] = None
    text: str = ""
    thought: str = ""
    raw_plan: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class HarnessValidation:
    ok: bool
    action: Optional[HarnessAction] = None
    reason: str = ""


def validate_harness_action(plan: Optional[Dict[str, Any]]) -> HarnessValidation:
    if not isinstance(plan, dict):
        return HarnessValidation(ok=False, reason="planner 未返回 JSON 对象。")
    action_name = _ACTION_ALIASES.get(str(plan.get("action") or "").strip().lower())
    if not action_name:
        return HarnessValidation(ok=False, reason=f"无法识别的 action：{plan.get('action')}")

    thought = _as_text(plan.get("thought"))
    text = _as_text(plan.get("text"))
    if action_name == "call_skill":
        skill = plan.get("skill")
        if not isinstance(skill, str) or not skill.strip():
            return HarnessValidation(ok=False, reason="call_skill 缺少有效的 skill 名称。")
        raw_args = plan.get("skill_args") or []
        if not isinstance(raw_args, list):
            return HarnessValidation(ok=False, reason="call_skill.skill_args 必须是数组。")
        return HarnessValidation(
            ok=True,
            action=HarnessAction(
                action=action_name,
                skill=skill.strip(),
                skill_args=[str(arg) for arg in raw_args],
                text=text,
                thought=thought,
                raw_plan=plan,
            ),
        )

    if action_name == "ask_clarification" and not text:
        return HarnessValidation(ok=False, reason="ask_clarification 缺少补充提问文本。")

    return HarnessValidation(
        ok=True,
        action=HarnessAction(
            action=action_name,
            text=text,
            thought=thought,
            raw_plan=plan,
        ),
    )


def _as_text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""
