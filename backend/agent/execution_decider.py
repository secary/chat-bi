"""Harness pre-audit for choosing the chat execution mode."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional

from backend.agent.executor import latest_user_content
from backend.agent.intent_guard import should_skip_skill_for_message
from backend.agent.multi_agent_intent import (
    classify_multi_agent_intent,
    route_sequence_from_intent,
)

ExecutionMode = Literal["single", "multi", "ask", "reject"]

_MULTI_INTENT_TYPES = {
    "period_compare",
    "query_then_decide",
    "query_then_viz",
    "query_then_decide_then_viz",
    "upload_then_analyze",
    "upload_then_viz",
}


@dataclass(frozen=True)
class ExecutionDecision:
    mode: ExecutionMode
    route_sequence: List[str]
    reason: str
    confidence: float
    risk_flags: List[str]
    intent: Optional[Dict[str, Any]] = None


def decide_execution_mode(messages: List[Dict[str, str]]) -> ExecutionDecision:
    """Choose a predictable execution mode from user intent and routing signals."""
    user_text = latest_user_content(messages)
    if not user_text:
        return ExecutionDecision(
            mode="ask",
            route_sequence=[],
            reason="用户问题为空，需要先补充问题。",
            confidence=1.0,
            risk_flags=["empty_message"],
        )

    if should_skip_skill_for_message(user_text):
        return ExecutionDecision(
            mode="single",
            route_sequence=[],
            reason="闲聊或解释类问题不需要多专线协作。",
            confidence=0.95,
            risk_flags=[],
        )

    intent = classify_multi_agent_intent(messages)
    if not intent:
        return ExecutionDecision(
            mode="single",
            route_sequence=[],
            reason="未命中结构化业务路由，使用单 Agent 直接回答。",
            confidence=0.72,
            risk_flags=["intent_unmatched"],
        )

    routes = route_sequence_from_intent(intent)
    intent_type = str(intent.get("intent_type") or "")
    risk_flags: List[str] = []
    if len(routes) > 1:
        risk_flags.append("composite_goal")
    if intent_type.startswith("upload_"):
        risk_flags.append("upload_context")
    if intent_type == "period_compare":
        risk_flags.append("cross_period")

    if intent_type == "query_only":
        return ExecutionDecision(
            mode="single",
            route_sequence=routes,
            reason="纯问数可由单 Agent 闭环，避免多专线额外耗时。",
            confidence=0.9,
            risk_flags=risk_flags,
            intent=intent,
        )

    if routes == ["business_advisor"]:
        return ExecutionDecision(
            mode="ask",
            route_sequence=routes,
            reason="用户只要求建议但缺少明确事实范围，需要先澄清分析对象或指标。",
            confidence=0.78,
            risk_flags=["decision_without_facts"],
            intent=intent,
        )

    if intent_type in _MULTI_INTENT_TYPES:
        return ExecutionDecision(
            mode="multi",
            route_sequence=routes,
            reason=str(intent.get("reason") or "复合目标需要先取事实再生成二阶产物。"),
            confidence=0.88 if len(routes) > 1 else 0.82,
            risk_flags=risk_flags,
            intent=intent,
        )

    return ExecutionDecision(
        mode="single",
        route_sequence=routes,
        reason="路由置信度不足或目标单一，使用单 Agent 执行。",
        confidence=0.68,
        risk_flags=risk_flags or ["low_route_confidence"],
        intent=intent,
    )
