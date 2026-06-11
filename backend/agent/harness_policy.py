from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

from backend.agent.executor import latest_user_upload_path
from backend.agent.harness_schema import HarnessAction
from backend.agent.harness_schema import HarnessValidation
from backend.agent.harness_state import HarnessState


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
) -> HarnessPolicyDecision:
    if action.action == "finish":
        return HarnessPolicyDecision(ok=True)
    if action.action != "call_skill":
        return HarnessPolicyDecision(ok=True)

    skill_name = action.skill or ""
    if skill_name not in set(available_skills):
        return HarnessPolicyDecision(ok=False, reason=f"skill 不在白名单：{skill_name}")

    if skill_name == "chatbi-decision-advisor" and not _has_query_result(state):
        if not _has_rows_result(state):
            return HarnessPolicyDecision(
                ok=False,
                reason="decision-advisor 必须在查询结果或结构化 rows 之后执行。",
                suggested_text="请先通过问数或上传分析技能产出结构化结果，再生成经营建议。",
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
            suggested_text="当前对话未检测到上传文件，请先上传文件，或改用演示库问数技能处理数据库问题。",
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


def _is_non_empty_list(value: object) -> bool:
    return isinstance(value, list) and bool(value)


def _rejection_obs(category: str, reason: str, extra: Dict[str, Any] | None = None) -> str:
    payload: Dict[str, Any] = {"ok": False, "category": category, "reason": reason}
    if extra:
        payload.update(extra)
    return json.dumps(payload, ensure_ascii=False)
