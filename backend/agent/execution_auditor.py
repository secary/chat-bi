"""Post-execution audit rules for remediation after single-agent runs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from backend.agent.executor import latest_user_content
from backend.agent.query_decision import is_query_plus_decision_text

_DECISION_MARKERS = (
    "经营建议",
    "决策意见",
    "管理建议",
    "下一步动作",
    "经营动作",
    "经营策略",
    "怎么做",
)

_VISUAL_MARKERS = (
    "图表",
    "画图",
    "可视化",
    "趋势图",
    "折线图",
    "柱状图",
    "饼图",
    "看板",
    "dashboard",
)


@dataclass(frozen=True)
class RemediationAction:
    skill: str
    reason: str


def audit_single_result_for_remediation(
    messages: List[Dict[str, str]],
    last_result: Optional[Dict[str, Any]],
    last_skill_name: Optional[str],
    emitted_types: List[str],
) -> List[RemediationAction]:
    """Return ordered follow-up actions when a single-agent answer missed requested outputs."""
    user_text = latest_user_content(messages)
    if not user_text or not isinstance(last_result, dict):
        return []

    actions: List[RemediationAction] = []
    if (
        _wants_decision(user_text)
        and _has_fact_result(last_result)
        and not _has_decision_result(last_result, last_skill_name)
    ):
        actions.append(
            RemediationAction(
                skill="chatbi-decision-advisor",
                reason="用户需要经营建议，但单 Agent 结果只有事实数据。",
            )
        )

    if (
        _wants_visual(user_text)
        and _has_rows(last_result)
        and not _has_visual_result(last_result, emitted_types)
    ):
        actions.append(
            RemediationAction(
                skill="chatbi-chart-recommendation",
                reason="用户需要图表或看板，但单 Agent 结果未产生可视化输出。",
            )
        )

    return actions


def _wants_decision(text: str) -> bool:
    return is_query_plus_decision_text(text) or any(marker in text for marker in _DECISION_MARKERS)


def _wants_visual(text: str) -> bool:
    lower = text.lower()
    return any(marker in text or marker.lower() in lower for marker in _VISUAL_MARKERS)


def _has_decision_result(result: Dict[str, Any], last_skill_name: Optional[str]) -> bool:
    if last_skill_name == "chatbi-decision-advisor":
        return True
    if str(result.get("kind") or "") == "decision":
        return True
    data = result.get("data")
    return isinstance(data, dict) and bool(data.get("advices"))


def _has_visual_result(result: Dict[str, Any], emitted_types: List[str]) -> bool:
    if any(kind in emitted_types for kind in ("chart", "kpi_cards", "dashboard_ready")):
        return True
    data = result.get("data")
    return bool(
        result.get("chart_plan")
        or result.get("charts")
        or result.get("kpis")
        or (isinstance(data, dict) and data.get("dashboard_middleware"))
    )


def _has_fact_result(result: Dict[str, Any]) -> bool:
    return _has_rows(result) or str(result.get("kind") or "") in {"table", "comparison"}


def _has_rows(result: Dict[str, Any]) -> bool:
    data = result.get("data")
    if not isinstance(data, dict):
        return False
    rows = data.get("rows")
    preview_rows = data.get("preview_rows")
    return (isinstance(rows, list) and bool(rows)) or (
        isinstance(preview_rows, list) and bool(preview_rows)
    )


def chart_recommendation_args(user_text: str, result: Dict[str, Any]) -> List[str]:
    data = result.get("data")
    rows: List[Any] = []
    if isinstance(data, dict):
        raw_rows = data.get("rows") or data.get("preview_rows")
        if isinstance(raw_rows, list):
            rows = raw_rows
    if not rows:
        return [user_text]
    import json

    return [json.dumps({"question": user_text, "rows": rows}, ensure_ascii=False)]
