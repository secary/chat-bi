from __future__ import annotations

from typing import Any, Dict, List

_GENERIC_MARKERS = (
    "加强管理",
    "持续跟进",
    "优化策略",
    "做好协同",
    "继续推进",
    "保持关注",
)

_EVIDENCE_MARKERS = ("%", "元", "月", "客户", "销售额", "毛利", "完成率", "留存")

_THEME_DIMENSION_MAP = {
    "区域经营": "区域",
    "渠道策略": "渠道",
    "产品组合": "产品类别",
    "客户运营": "客户类型",
    "销售趋势": "月份",
}


def audit_decision_result(result: Dict[str, Any]) -> Dict[str, Any]:
    data = result.get("data")
    if not isinstance(data, dict):
        return {
            "status": "warning",
            "issues": [
                _issue(
                    "DECISION_PAYLOAD_MISSING", "warning", "缺少结构化决策结果，无法执行内容审核。"
                )
            ],
        }

    facts = data.get("facts")
    advices = data.get("advices")
    issues: List[Dict[str, str]] = []
    if not isinstance(facts, dict):
        issues.append(
            _issue(
                "FACTS_MISSING_FOR_DECISION",
                "error",
                "决策建议缺少 facts，无法确认建议是否有数据依据。",
            )
        )
        return _result(issues)
    if not isinstance(advices, list):
        issues.append(
            _issue(
                "ADVICES_MISSING_FOR_DECISION",
                "error",
                "决策建议缺少 advices 结构，无法确认输出内容。",
            )
        )
        return _result(issues)

    overview = facts.get("overview")
    scope = facts.get("scope") if isinstance(facts.get("scope"), dict) else {}
    focus_dimensions = {
        str(item).strip() for item in (scope.get("focus_dimensions") or []) if str(item).strip()
    }

    if not isinstance(overview, dict) or not _has_core_decision_facts(overview):
        issues.append(
            _issue(
                "FACTS_MISSING_FOR_DECISION",
                "error",
                "决策建议缺少销售额、目标完成率或毛利率等关键事实。",
            )
        )

    if not advices:
        issues.append(
            _issue("DECISION_ADVICE_EMPTY", "warning", "已生成决策结果，但没有可执行建议。")
        )
        return _result(issues)

    if _has_scope_mismatch(advices, focus_dimensions):
        issues.append(
            _issue("DECISION_SCOPE_MISMATCH", "warning", "建议主题与当前问题聚焦维度不一致。")
        )

    generic_count = 0
    unsupported_count = 0
    incomplete_count = 0
    for advice in advices:
        if not isinstance(advice, dict):
            continue
        decision = str(advice.get("decision") or "").strip()
        reason = str(advice.get("reason") or "").strip()
        actions = advice.get("actions") if isinstance(advice.get("actions"), list) else []
        if not decision or not reason or not actions:
            incomplete_count += 1
        if _is_generic_advice(decision, actions):
            generic_count += 1
        if not _has_grounding_evidence(reason):
            unsupported_count += 1

    if incomplete_count:
        issues.append(
            _issue(
                "DECISION_ADVICE_INCOMPLETE",
                "warning",
                f"有 {incomplete_count} 条建议缺少依据或行动项。",
            )
        )
    if generic_count:
        issues.append(
            _issue(
                "DECISION_ADVICE_TOO_GENERIC",
                "warning",
                f"有 {generic_count} 条建议表述偏泛，缺少明确对象或动作。",
            )
        )
    if unsupported_count:
        issues.append(
            _issue(
                "DECISION_ADVICE_NOT_GROUNDED",
                "warning",
                f"有 {unsupported_count} 条建议依据里缺少明显的业务事实证据。",
            )
        )

    return _result(issues)


def _has_core_decision_facts(overview: Dict[str, Any]) -> bool:
    keys = ("sales", "target_achievement_rate", "gross_margin_rate")
    return all(str(overview.get(key) or "").strip() not in {"", "NULL", "None"} for key in keys)


def _has_scope_mismatch(advices: List[Any], focus_dimensions: set[str]) -> bool:
    if not focus_dimensions:
        return False
    allowed_themes = {
        theme for theme, dimension in _THEME_DIMENSION_MAP.items() if dimension in focus_dimensions
    }
    allowed_themes.update({"增长目标", "目标补差", "盈利质量"})
    for advice in advices:
        if not isinstance(advice, dict):
            continue
        theme = str(advice.get("theme") or "").strip()
        if theme and theme not in allowed_themes:
            return True
    return False


def _is_generic_advice(decision: str, actions: List[Any]) -> bool:
    text = f"{decision} {' '.join(str(item) for item in actions)}"
    return any(marker in text for marker in _GENERIC_MARKERS)


def _has_grounding_evidence(reason: str) -> bool:
    return any(marker in reason for marker in _EVIDENCE_MARKERS) or any(
        ch.isdigit() for ch in reason
    )


def _issue(code: str, level: str, message: str) -> Dict[str, str]:
    return {"code": code, "level": level, "message": message}


def _result(issues: List[Dict[str, str]]) -> Dict[str, Any]:
    status = "ok"
    levels = {issue["level"] for issue in issues}
    if "error" in levels:
        status = "error"
    elif "warning" in levels:
        status = "warning"
    return {"status": status, "issues": issues, "issue_count": len(issues)}
