from __future__ import annotations

from typing import Any, Dict, List

from backend.agent.harness_business_flows import summarize_business_flows
from backend.agent.harness_audit_rules import evaluate_audit_rules
from backend.trace_repo import list_recent_trace_ids, list_trace_events


def build_audit_report(trace_id: str) -> Dict[str, Any]:
    events = list_trace_events(trace_id)
    issues = evaluate_audit_rules(events)
    business_flows = summarize_business_flows(events)
    status = _status_for_issues(issues)
    return {
        "trace_id": trace_id,
        "status": status,
        "score": _score_for_issues(issues),
        "summary": _summary(status, issues),
        "issues": issues,
        "business_flows": business_flows,
        "events": events,
        "event_count": len(events),
    }


def list_recent_audit_candidates(limit: int = 20) -> List[Dict[str, Any]]:
    return list_recent_trace_ids(limit)


def _status_for_issues(issues: List[Dict[str, Any]]) -> str:
    levels = {issue.get("level") for issue in issues}
    if "error" in levels:
        return "error"
    if "warning" in levels:
        return "warning"
    return "ok"


def _score_for_issues(issues: List[Dict[str, Any]]) -> int:
    score = 100
    for issue in issues:
        level = issue.get("level")
        if level == "error":
            score -= 25
        elif level == "warning":
            score -= 10
        elif level == "info":
            score -= 2
    return max(0, score)


def _summary(status: str, issues: List[Dict[str, Any]]) -> str:
    if not issues:
        return "未发现明显异常。"
    if status == "error":
        return "检测到需要优先处理的链路异常。"
    if status == "warning":
        return "链路可完成，但存在可疑波动或约束回退。"
    return "链路整体正常，仅有轻微提示。"
