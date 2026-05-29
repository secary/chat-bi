"""Post-execution audit and remediation rules for agent runs."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional

from backend.agent.decision_content_audit import audit_decision_result
from backend.agent.executor import latest_user_content
from backend.agent.query_decision import is_query_plus_decision_text

AuditStatus = Literal["ok", "warning", "error"]

# fmt: off
_DECISION_MARKERS = ("经营建议", "决策意见", "管理建议", "下一步动作", "经营动作", "经营策略", "怎么做", "建议")
_VISUAL_MARKERS = ("图表", "画图", "可视化", "趋势图", "折线图", "柱状图", "饼图", "看板", "dashboard")
# fmt: on
_FACT_AGENT_IDS = {"demo_query", "upload_analyst", "period_compare"}
_DECISION_AGENT_IDS = {"business_advisor"}
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


def audit_multi_final_synthesis(
    *,
    user_question: str,
    blocks: List[Dict[str, str]],
    last_result: Optional[Dict[str, Any]],
    last_skill_name: Optional[str],
    dependency_warnings: List[str],
) -> FinalAudit:
    """Ensure final multi-agent synthesis is grounded in upstream facts."""
    issues: List[Dict[str, str]] = []
    fact_blocks = _fact_blocks(blocks)
    decision_blocks = [
        block for block in blocks if str(block.get("agent") or "") in _DECISION_AGENT_IDS
    ]

    if dependency_warnings:
        issues.append(
            _issue(
                "SUMMARY_DEPENDENCY_UNMET",
                "warning",
                "部分下游专线声明缺少依赖事实，最终回答需要收束到已有事实。",
            )
        )

    if _wants_decision(user_question) and decision_blocks and not fact_blocks:
        issues.append(
            _issue(
                "DECISION_WITHOUT_UPSTREAM_FACTS",
                "error",
                "经营建议专线没有可审计的上游事实结果，禁止直接生成建议汇总。",
            )
        )

    if isinstance(last_result, dict) and (
        last_skill_name == "chatbi-decision-advisor"
        or str(last_result.get("kind") or "") == "decision"
    ):
        audit = audit_decision_result(last_result)
        if audit.get("status") == "error":
            issues.append(
                _issue(
                    "DECISION_CONTENT_AUDIT_ERROR",
                    "error",
                    "决策结果缺少 facts 或关键事实，禁止作为最终建议依据。",
                )
            )

    fact_ledger = build_fact_ledger(fact_blocks)
    return FinalAudit(status=_status(issues), issues=issues, fact_ledger=fact_ledger)


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
            "已确认：本轮已读取并处理上传文件。你可以继续指定要分析的指标、字段、分组维度或时间范围，我会基于文件数据重新计算。"
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


def build_fact_ledger(blocks: List[Dict[str, str]]) -> str:
    lines: List[str] = []
    for idx, block in enumerate(blocks, start=1):
        observation = _clean_observation(str(block.get("observation") or ""))
        if not observation:
            continue
        lines.append(f"- 事实 {idx}: {observation[:600]}")
    return "\n".join(lines)


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


def _fact_blocks(blocks: List[Dict[str, str]]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for block in blocks:
        agent = str(block.get("agent") or "")
        observation = str(block.get("observation") or "")
        if agent in _FACT_AGENT_IDS or _looks_like_fact_observation(observation):
            out.append(block)
    return out


def _looks_like_fact_observation(observation: str) -> bool:
    return any(
        marker in observation
        for marker in ("rows", "查询", "销售额", "毛利", "完成率", "SQL", "已读取", "共返回")
    )


def _looks_like_advice(text: str) -> bool:
    return any(
        marker in text for marker in ("建议", "应当", "优先", "需要", "下一步", "策略", "动作")
    )


def _normalized_numbers(text: str) -> set[str]:
    numbers: set[str] = set()
    for match in _NUMBER_RE.findall(text or ""):
        token = match.replace(",", "")
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


def _clean_observation(text: str) -> str:
    return " ".join(text.strip().split())


def _issue(code: str, level: str, message: str) -> Dict[str, str]:
    return {"code": code, "level": level, "message": message}


def _status(issues: List[Dict[str, str]]) -> AuditStatus:
    levels = {issue["level"] for issue in issues}
    if "error" in levels:
        return "error"
    if "warning" in levels:
        return "warning"
    return "ok"
