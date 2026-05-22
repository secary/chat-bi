from __future__ import annotations

from typing import Any, Dict, List

_FACT_CODES = {"FACTS_MISSING_FOR_DECISION"}
_QUALITY_CODES = {
    "DECISION_ADVICE_TOO_GENERIC",
    "DECISION_ADVICE_NOT_GROUNDED",
    "DECISION_ADVICE_INCOMPLETE",
    "DECISION_ADVICE_EMPTY",
}
_SCOPE_CODES = {"DECISION_SCOPE_MISMATCH"}


def summarize_decision_content_audit_flow(events: List[Dict[str, Any]]) -> Dict[str, Any] | None:
    audit = _latest_decision_audit(events)
    if not audit:
        return None

    issues = audit.get("issues") if isinstance(audit.get("issues"), list) else []
    codes = {str(item.get("code") or "").strip() for item in issues if isinstance(item, dict)}
    status = _audit_status(audit)

    steps = [
        {
            "key": "facts_grounding",
            "label": "事实依据",
            "status": "error" if codes & _FACT_CODES else "completed",
            "detail": (
                "决策建议缺少关键经营事实，当前结论不可靠。"
                if codes & _FACT_CODES
                else "已检测到销售额、目标完成率、毛利率等关键事实支撑。"
            ),
        },
        {
            "key": "advice_quality",
            "label": "建议质量",
            "status": _quality_status(codes),
            "detail": _quality_detail(codes),
        },
        {
            "key": "scope_consistency",
            "label": "范围一致性",
            "status": "warning" if codes & _SCOPE_CODES else "completed",
            "detail": (
                "建议主题与当前问题聚焦维度存在偏移。"
                if codes & _SCOPE_CODES
                else "建议主题与当前问题范围保持一致。"
            ),
        },
    ]

    return {
        "flow_key": "decision_content_audit",
        "title": "决策建议内容审核",
        "status": status,
        "summary": _summary(status, len(issues)),
        "steps": steps,
    }


def _latest_decision_audit(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    for event in reversed(events):
        if (
            event.get("span_name") != "agent.harness"
            or event.get("event_name") != "observation_built"
        ):
            continue
        payload = event.get("payload") or {}
        audit = payload.get("decision_content_audit")
        if isinstance(audit, dict):
            return audit
    return {}


def _audit_status(audit: Dict[str, Any]) -> str:
    raw = str(audit.get("status") or "").strip().lower()
    if raw == "error":
        return "error"
    if raw == "warning":
        return "warning"
    return "completed"


def _quality_status(codes: set[str]) -> str:
    if codes & _FACT_CODES:
        return "pending"
    if codes & _QUALITY_CODES:
        return "warning"
    return "completed"


def _quality_detail(codes: set[str]) -> str:
    if codes & _FACT_CODES:
        return "需先补齐核心事实，再判断建议文本质量。"
    if "DECISION_ADVICE_TOO_GENERIC" in codes and "DECISION_ADVICE_NOT_GROUNDED" in codes:
        return "建议存在套话倾向，且依据里缺少明显业务证据。"
    if "DECISION_ADVICE_TOO_GENERIC" in codes:
        return "建议表述偏泛，缺少明确对象或动作。"
    if "DECISION_ADVICE_NOT_GROUNDED" in codes:
        return "建议依据里缺少明显的业务事实证据。"
    if "DECISION_ADVICE_INCOMPLETE" in codes:
        return "部分建议缺少依据或行动项。"
    if "DECISION_ADVICE_EMPTY" in codes:
        return "当前没有形成可执行建议。"
    return "建议文本已通过基础规则审核。"


def _summary(status: str, issue_count: int) -> str:
    if status == "error":
        return "决策建议内容审核未通过，存在关键事实缺失。"
    if status == "warning":
        return f"决策建议已完成内容审核，发现 {issue_count} 个需关注项。"
    return "决策建议已完成内容审核，当前未发现明显风险。"
