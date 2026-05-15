"""Pre-execution validation for skill calls (metadata-driven + allowlist)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

from backend.agent.prompt_builder import SkillDoc
from backend.agent.upload_path_detect import has_upload_file_reference

_METRIC_QUERY_RE = re.compile(
    r"(销售额|毛利|利润|营收|收入|排行|排名|趋势|汇总|指标|kpi|客户|订单|区域|渠道|产品)",
    re.IGNORECASE,
)


def _has_metric_query_keywords(text: str) -> bool:
    if not text:
        return False
    return bool(_METRIC_QUERY_RE.search(text))


def dialogue_text_from_messages(messages: List[Dict[str, str]]) -> str:
    parts: List[str] = []
    for m in messages:
        c = str(m.get("content") or "").strip()
        if c:
            parts.append(c)
    return "\n".join(parts)


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    reason: str = ""
    rule: str = ""


def _has_followup_rows(last_result: Optional[Dict[str, Any]]) -> bool:
    if not isinstance(last_result, dict):
        return False
    data = last_result.get("data")
    if not isinstance(data, dict):
        return False
    rows = data.get("rows")
    if isinstance(rows, list) and rows:
        return True
    preview = data.get("preview_rows")
    return isinstance(preview, list) and bool(preview)


def _has_prior_observation(last_result: Optional[Dict[str, Any]]) -> bool:
    if not isinstance(last_result, dict):
        return False
    if last_result.get("ok") is False:
        return False
    if _has_followup_rows(last_result):
        return True
    data = last_result.get("data")
    if isinstance(data, dict) and data:
        return True
    if last_result.get("text") or last_result.get("charts") or last_result.get("kpis"):
        return True
    return False


def validate_skill_call(
    skill_doc: SkillDoc,
    *,
    allowed_slugs: Set[str],
    dialogue_text: str,
    last_result: Optional[Dict[str, Any]],
    user_text: str,
) -> ValidationResult:
    slug = skill_doc.skill_dir.name
    if slug not in allowed_slugs:
        return ValidationResult(
            ok=False,
            reason=f"技能「{slug}」不在当前可用列表中，请改选其它技能或 finish 说明原因。",
            rule="allowed_slugs",
        )

    requires = list(skill_doc.validator_requires or [])
    if not requires:
        return ValidationResult(ok=True)

    blob = dialogue_text or user_text or ""
    for req in requires:
        if req == "prior_observation":
            if not _has_prior_observation(last_result):
                return ValidationResult(
                    ok=False,
                    reason=(
                        f"技能「{slug}」需要先有上一步工具 Observation（表格或查询结果），"
                        "请先调用取数技能或 finish 说明缺数据。"
                    ),
                    rule="prior_observation",
                )
        elif req == "no_upload_path_in_thread":
            if has_upload_file_reference(blob):
                return ValidationResult(
                    ok=False,
                    reason=(
                        f"技能「{slug}」仅用于演示库问数；对话含上传文件路径时"
                        "应使用 chatbi-file-ingestion / chatbi-auto-analysis。"
                    ),
                    rule="no_upload_path_in_thread",
                )
        elif req == "upload_path_or_rows":
            if not has_upload_file_reference(blob) and not _has_followup_rows(last_result):
                return ValidationResult(
                    ok=False,
                    reason=(
                        f"技能「{slug}」需要上传文件路径或上一步已解析的表格 rows，"
                        "请先 chatbi-file-ingestion。"
                    ),
                    rule="upload_path_or_rows",
                )
        elif req == "no_metric_query_in_thread":
            if _has_metric_query_keywords(blob):
                return ValidationResult(
                    ok=False,
                    reason=(
                        f"技能「{slug}」仅用于库表/Schema概览查询；"
                        "用户问数涉及业务指标、排行、趋势时应用 chatbi-semantic-query。"
                    ),
                    rule="no_metric_query_in_thread",
                )

    return ValidationResult(ok=True)


def validation_observation_payload(
    skill_name: str,
    result: ValidationResult,
    allowed_slugs: Set[str],
) -> str:
    import json

    payload: Dict[str, Any] = {
        "skill": skill_name,
        "ok": False,
        "error": "skill_validation_rejected",
        "reason": result.reason,
        "rule": result.rule,
        "allowed_skills": sorted(allowed_slugs),
    }
    return json.dumps(payload, ensure_ascii=False)
