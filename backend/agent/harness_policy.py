from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

from backend.agent.executor import latest_user_upload_path
from backend.agent.harness_schema import HarnessAction
from backend.agent.harness_schema import HarnessValidation
from backend.agent.harness_state import HarnessState

_STRONGLY_SCOPED_SKILLS = {
    "chatbi-file-ingestion",
    "chatbi-auto-analysis",
    "chatbi-comparison",
    "chatbi-alias-manager",
}


@dataclass(frozen=True)
class HarnessPolicyDecision:
    ok: bool
    reason: str = ""
    suggested_text: str = ""


def rejection_observation(
    validation: HarnessValidation | None, policy: HarnessPolicyDecision | None
) -> str:
    if validation and not validation.ok:
        return _rejection_obs("schema_rejected", validation.reason)
    if policy and not policy.ok:
        return _rejection_obs("policy_rejected", policy.reason)
    return _rejection_obs("unknown_rejected", "未知 Harness 拒绝。")


def authorize_action(
    action: HarnessAction,
    state: HarnessState,
    available_skills: Sequence[str],
    messages: Optional[List[dict]] = None,
    specialist_agent_id: Optional[str] = None,
    preferred_skills: Optional[Sequence[str]] = None,
) -> HarnessPolicyDecision:
    if action.action == "finish":
        finish_block = _finish_blocker(
            action,
            state,
            specialist_agent_id=specialist_agent_id,
        )
        if finish_block is not None:
            return finish_block
        return HarnessPolicyDecision(ok=True)
    if action.action != "call_skill":
        return HarnessPolicyDecision(ok=True)

    skill_name = action.skill or ""
    if (
        specialist_agent_id
        and preferred_skills is not None
        and skill_name in _STRONGLY_SCOPED_SKILLS
        and skill_name not in set(preferred_skills)
    ):
        return HarnessPolicyDecision(
            ok=False,
            reason=(
                f"{specialist_agent_id} 当前不应调取 {skill_name}；"
                "请改派更合适的专线或重新选择技能。"
            ),
            suggested_text=_scoped_skill_suggestion(skill_name),
        )

    if skill_name not in set(available_skills):
        return HarnessPolicyDecision(ok=False, reason=f"skill 不在白名单：{skill_name}")

    if skill_name == "chatbi-decision-advisor" and not _has_query_result(state):
        if not _has_rows_result(state):
            return HarnessPolicyDecision(
                ok=False,
                reason="decision-advisor 必须在查询结果或结构化 rows 之后执行。",
                suggested_text="请先由问数或上传分析专线产出结构化结果，再生成经营建议。",
            )

    if skill_name == "chatbi-auto-analysis" and not (
        _has_rows_result(state) or _has_upload(messages)
    ):
        return HarnessPolicyDecision(
            ok=False,
            reason=f"{skill_name} 需要已有结构化 rows 或上传文件上下文。",
            suggested_text="请先完成文件读取或提供结构化 rows，再执行上传分析/采纳指标。",
        )

    if skill_name == "chatbi-file-ingestion" and not _has_upload(messages):
        return HarnessPolicyDecision(
            ok=False,
            reason="file-ingestion 需要上传文件上下文。",
            suggested_text="当前对话未检测到上传文件，请先上传文件，或改用演示库问数专线处理数据库问题。",
        )

    return HarnessPolicyDecision(ok=True)


def _has_upload(messages: Optional[List[dict]]) -> bool:
    return bool(messages) and bool(latest_user_upload_path(messages or []))


def _has_query_result(state: HarnessState) -> bool:
    return bool(state.last_result) and state.last_skill_name == "chatbi-semantic-query"


def _has_rows_result(state: HarnessState) -> bool:
    result = state.last_result
    if not isinstance(result, dict):
        return False
    data = result.get("data")
    if not isinstance(data, dict):
        return False
    rows = data.get("rows")
    preview_rows = data.get("preview_rows")
    return _is_non_empty_list(rows) or _is_non_empty_list(preview_rows)


def _has_decision_result(state: HarnessState) -> bool:
    result = state.last_result
    if not isinstance(result, dict):
        return False
    if state.last_skill_name == "chatbi-decision-advisor":
        return True
    return str(result.get("kind") or "") == "decision"


def _finish_blocker(
    action: HarnessAction,
    state: HarnessState,
    *,
    specialist_agent_id: Optional[str],
) -> HarnessPolicyDecision | None:
    if specialist_agent_id != "business_advisor":
        return None
    if _has_decision_result(state):
        return None
    return HarnessPolicyDecision(
        ok=False,
        reason="business_advisor 不能在未执行 chatbi-decision-advisor 前直接 finish。",
        suggested_text=(
            "请先基于已有查询结果调用经营建议技能；若仍缺少结构化结果，请改派问数或上传分析专线。"
        ),
    )


def _is_non_empty_list(value: object) -> bool:
    return isinstance(value, list) and bool(value)


def _scoped_skill_suggestion(skill_name: str) -> str:
    suggestions = {
        "chatbi-file-ingestion": "请改派上传与文件分析专线，并先执行文件读取与结构校验。",
        "chatbi-auto-analysis": "请改派上传与文件分析专线执行 auto-analysis；若尚无 rows，请先完成 file-ingestion。",
        "chatbi-comparison": "请改派环比与经营对比专线处理跨期对比问题。",
        "chatbi-alias-manager": "请改派语义别名专线维护指标/维度别名。",
    }
    return suggestions.get(skill_name, "请改派更合适的专线，或补齐该技能的前置条件后再继续。")


def _rejection_obs(category: str, reason: str, extra: Dict[str, Any] | None = None) -> str:
    payload: Dict[str, Any] = {"ok": False, "category": category, "reason": reason}
    if extra:
        payload.update(extra)
    return json.dumps(payload, ensure_ascii=False)
