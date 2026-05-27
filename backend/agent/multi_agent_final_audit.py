"""Final audit gate for multi-agent synthesis."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional

from backend.agent.decision_content_audit import audit_decision_result

AuditStatus = Literal["ok", "warning", "error"]

_FACT_AGENT_IDS = {"demo_query", "upload_analyst", "period_compare"}
_DECISION_AGENT_IDS = {"business_advisor"}
_DECISION_MARKERS = (
    "经营建议",
    "决策意见",
    "管理建议",
    "下一步动作",
    "怎么做",
    "建议",
)


@dataclass(frozen=True)
class MultiFinalAudit:
    status: AuditStatus
    issues: List[Dict[str, str]]
    fact_ledger: str

    @property
    def should_block_summary(self) -> bool:
        return self.status == "error"


def audit_multi_final_synthesis(
    *,
    user_question: str,
    blocks: List[Dict[str, str]],
    last_result: Optional[Dict[str, Any]],
    last_skill_name: Optional[str],
    dependency_warnings: List[str],
) -> MultiFinalAudit:
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
    return MultiFinalAudit(status=_status(issues), issues=issues, fact_ledger=fact_ledger)


def build_factual_fallback(audit: MultiFinalAudit) -> str:
    issue_lines = "\n".join(f"- {issue['message']}" for issue in audit.issues)
    if audit.fact_ledger:
        return (
            "本轮多专线结果未通过最终事实审计，因此先不生成新的经营建议或扩展解读。\n\n"
            "审计发现：\n"
            f"{issue_lines}\n\n"
            "已确认的事实依据：\n"
            f"{audit.fact_ledger}"
        )
    return (
        "本轮多专线结果未通过最终事实审计，因此先不生成经营建议。\n\n"
        "审计发现：\n"
        f"{issue_lines}\n\n"
        "当前没有取得可用于支撑建议的结构化事实，请先补充查询指标、时间范围或区域。"
    )


def build_fact_ledger(blocks: List[Dict[str, str]]) -> str:
    lines: List[str] = []
    for idx, block in enumerate(blocks, start=1):
        observation = _clean_observation(str(block.get("observation") or ""))
        if not observation:
            continue
        lines.append(f"- 事实 {idx}: {observation[:600]}")
    return "\n".join(lines)


def _fact_blocks(blocks: List[Dict[str, str]]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for block in blocks:
        agent = str(block.get("agent") or "")
        observation = str(block.get("observation") or "")
        if agent in _FACT_AGENT_IDS or _looks_like_fact_observation(observation):
            out.append(block)
    return out


def _looks_like_fact_observation(observation: str) -> bool:
    markers = ("rows", "查询", "销售额", "毛利", "完成率", "SQL", "已读取", "共返回")
    return any(marker in observation for marker in markers)


def _wants_decision(text: str) -> bool:
    return any(marker in text for marker in _DECISION_MARKERS)


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
