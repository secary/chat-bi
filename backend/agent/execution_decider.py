"""Harness pre-audit for single-agent chat execution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional

from backend.agent.executor import latest_user_content
from backend.agent.intent_guard import should_skip_skill_for_message

ExecutionMode = Literal["single", "ask", "reject"]

_BUSINESS_DECISION_MARKERS = (
    "经营建议",
    "决策建议",
    "决策意见",
    "管理建议",
    "下一步动作",
    "经营动作",
    "经营策略",
)
_QUERY_MARKERS = (
    "查",
    "查询",
    "统计",
    "分析",
    "排行",
    "趋势",
    "销售额",
    "毛利",
    "毛利率",
    "完成率",
    "留存",
    "同比",
    "环比",
    "数据库",
    "表",
)
_VISUAL_MARKERS = ("图表", "画图", "可视化", "趋势图", "折线图", "柱状图", "饼图", "看板")


@dataclass(frozen=True)
class ExecutionDecision:
    mode: ExecutionMode
    route_sequence: List[str]
    reason: str
    confidence: float
    risk_flags: List[str]
    intent: Optional[Dict[str, Any]] = None


def decide_execution_mode(messages: List[Dict[str, str]]) -> ExecutionDecision:
    """Choose whether single-agent execution needs clarification first."""
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
            reason="闲聊或解释类问题不需要调用业务工具。",
            confidence=0.95,
            risk_flags=[],
        )

    routes = _route_sequence(user_text)
    risk_flags: List[str] = []
    if len(routes) > 1:
        risk_flags.append("composite_goal")
    if "上传" in user_text or "附件" in user_text:
        risk_flags.append("upload_context")
    if "同比" in user_text or "环比" in user_text or "相比" in user_text:
        risk_flags.append("cross_period")

    if routes == ["business_advisor"]:
        return ExecutionDecision(
            mode="ask",
            route_sequence=routes,
            reason="用户只要求建议但缺少明确事实范围，需要先澄清分析对象或指标。",
            confidence=0.78,
            risk_flags=["decision_without_facts"],
        )

    if routes:
        return ExecutionDecision(
            mode="single",
            route_sequence=routes,
            reason="业务请求由单 Agent 按需调用工具闭环处理。",
            confidence=0.9 if routes == ["demo_query"] else 0.82,
            risk_flags=risk_flags,
        )

    return ExecutionDecision(
        mode="single",
        route_sequence=[],
        reason="未命中结构化业务路由，使用单 Agent 直接回答。",
        confidence=0.72,
        risk_flags=["intent_unmatched"],
    )


def _route_sequence(user_text: str) -> List[str]:
    wants_query = any(marker in user_text for marker in _QUERY_MARKERS)
    wants_decision = any(marker in user_text for marker in _BUSINESS_DECISION_MARKERS)
    wants_visual = any(marker in user_text for marker in _VISUAL_MARKERS)

    if wants_query:
        routes = ["demo_query"]
        if wants_decision:
            routes.append("business_advisor")
        elif wants_visual:
            routes.append("viz_board")
        return routes

    if wants_decision:
        return ["business_advisor"]
    return []
