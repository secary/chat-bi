"""Post-execution audit and remediation rules for agent runs."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional

from backend.agent.executor import latest_user_content
from backend.agent.query_decision import is_query_plus_decision_text

AuditStatus = Literal["ok", "warning", "error"]

# fmt: off
_DECISION_MARKERS = ("经营建议", "决策意见", "管理建议", "下一步动作", "经营动作", "经营策略", "怎么做", "建议")
_VISUAL_MARKERS = ("图表", "画图", "可视化", "趋势图", "折线图", "柱状图", "饼图", "看板", "dashboard")
# fmt: on
_NUMBER_RE = re.compile(r"(?<![A-Za-z0-9])\d[\d,]*(?:\.\d+)?%?")


@dataclass(frozen=True)
class RemediationAction:
    skill: str
    reason: str


@dataclass(frozen=True)
class FinalAudit:
    status: AuditStatus
    issues: List[Dict[str, str]]
    fact_ledger: str

    @property
    def should_block_summary(self) -> bool:
        return self.status == "error"


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


def audit_summary_against_fact_ledger(
    *,
    summary_text: str,
    fact_ledger: str,
) -> FinalAudit:
    """Audit generated summary claims against the final fact ledger."""
    issues: List[Dict[str, str]] = []
    summary_numbers = _normalized_numbers(summary_text)
    ledger_numbers = _normalized_numbers(fact_ledger)
    unsupported = sorted(number for number in summary_numbers if number not in ledger_numbers)

    if unsupported:
        issues.append(
            _issue(
                "SUMMARY_NUMERIC_CLAIM_NOT_IN_FACT_LEDGER",
                "error",
                f"最终汇总出现事实账本中不存在的数字：{', '.join(unsupported[:5])}。",
            )
        )

    if _looks_like_advice(summary_text) and not fact_ledger.strip():
        issues.append(
            _issue(
                "SUMMARY_ADVICE_WITHOUT_FACT_LEDGER",
                "error",
                "最终汇总包含建议表述，但没有可审计的事实账本。",
            )
        )

    return FinalAudit(status=_status(issues), issues=issues, fact_ledger=fact_ledger)


def build_factual_fallback(audit: FinalAudit) -> str:
    issue_lines = "\n".join(f"- {issue['message']}" for issue in audit.issues)
    if audit.fact_ledger:
        return (
            "本轮回答的部分数字未通过事实审计，因此先不生成新的经营建议或扩展解读。\n\n"
            "审计发现：\n"
            f"{issue_lines}\n\n"
            "已确认：本轮已有可审计的结构化结果。你可以继续指定要分析的指标、字段、分组维度或时间范围，我会基于本轮结果重新整理。"
        )
    return (
        "本轮回答未通过事实审计，因此先不生成经营建议。\n\n"
        "审计发现：\n"
        f"{issue_lines}\n\n"
        "当前没有取得可用于支撑建议的结构化事实，请先补充查询指标、时间范围或区域。"
    )


def chart_recommendation_args(user_text: str, result: Dict[str, Any]) -> List[str]:
    rows = _rows(result)
    if not rows:
        return [user_text]
    return [json.dumps({"question": user_text, "rows": rows}, ensure_ascii=False)]


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
    return bool(_rows(result))


def _rows(result: Dict[str, Any]) -> List[Any]:
    data = result.get("data")
    if not isinstance(data, dict):
        return []
    raw_rows = data.get("rows") or data.get("preview_rows")
    return raw_rows if isinstance(raw_rows, list) else []


def _looks_like_advice(text: str) -> bool:
    return any(
        marker in text for marker in ("建议", "应当", "优先", "需要", "下一步", "策略", "动作")
    )


def _normalized_numbers(text: str) -> set[str]:
    numbers: set[str] = set()
    source = text or ""
    for match in _NUMBER_RE.finditer(source):
        if _is_temporal_number_context(source, match.start(), match.end()):
            continue
        token = match.group(0).replace(",", "")
        if token.endswith("%"):
            core = token[:-1]
            suffix = "%"
        else:
            core = token
            suffix = ""
        if "." in core:
            core = core.rstrip("0").rstrip(".")
        numbers.add(f"{core}{suffix}")
    return numbers


def _is_temporal_number_context(text: str, start: int, end: int) -> bool:
    before = text[max(0, start - 4) : start]
    after = text[end : min(len(text), end + 4)]
    window = text[max(0, start - 4) : min(len(text), end + 4)]
    if after.startswith(("月", "月份", "年")):
        return True
    if before.endswith(("年", "第")) and after.startswith(("月", "季度", "季")):
        return True
    if "月" in window and any(sep in window for sep in ("-", "—", "至", "到", "、", ",")):
        return True
    return False


def _issue(code: str, level: str, message: str) -> Dict[str, str]:
    return {"code": code, "level": level, "message": message}


def _status(issues: List[Dict[str, str]]) -> AuditStatus:
    levels = {issue["level"] for issue in issues}
    if "error" in levels:
        return "error"
    if "warning" in levels:
        return "warning"
    return "ok"
