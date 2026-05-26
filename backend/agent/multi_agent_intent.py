"""Controlled intent classification for multi-agent routing."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.agent.data_source_intent import DataSourceIntent, resolve_data_source

_DECISION_STRONG_KEYWORDS = (
    "经营建议",
    "决策意见",
    "管理建议",
    "下一步动作",
    "经营动作",
    "经营策略",
    "怎么做",
)

_DECISION_ADVICE_KEYWORD = "建议"

_VIZ_KEYWORDS = (
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

_COMPARE_KEYWORDS = ("环比", "同比", "比上月", "较上月", "对比")

_QUERY_KEYWORDS = (
    "查",
    "查询",
    "统计",
    "分析",
    "销售",
    "毛利",
    "目标",
    "完成率",
    "客户",
    "留存",
    "区域",
    "渠道",
    "产品",
    "趋势",
    "排行",
)


def classify_multi_agent_intent(messages: List[Dict[str, str]]) -> Optional[Dict[str, Any]]:
    user_text = _latest_user_text(messages)
    if not user_text:
        return None

    data_source = resolve_data_source(messages)
    wants_viz = _contains_any(user_text, _VIZ_KEYWORDS)
    wants_compare = _contains_any(user_text, _COMPARE_KEYWORDS)
    wants_query = _contains_any(user_text, _QUERY_KEYWORDS)
    wants_decision = _wants_decision(user_text, wants_query=wants_query, wants_viz=wants_viz)

    routes: List[str] = []
    if data_source == DataSourceIntent.UPLOAD_FILE:
        routes.append("upload_analyst")
    elif wants_compare:
        routes.append("period_compare")
    elif wants_query or wants_viz:
        routes.append("demo_query")

    if wants_decision and "business_advisor" not in routes:
        routes.append("business_advisor")
    if wants_viz and "viz_board" not in routes:
        routes.append("viz_board")

    if not routes:
        return None

    intent_type = _intent_type(routes, wants_decision=wants_decision, wants_viz=wants_viz)
    return {
        "intent_type": intent_type,
        "current_route": routes[0],
        "route_sequence": routes,
        "primary_text": user_text,
        "final_outputs": _final_outputs(wants_decision=wants_decision, wants_viz=wants_viz),
        "summary": _summary(intent_type, routes),
        "reason": "受控意图识别根据用户原话、数据源线索和复合目标建立路由序列。",
    }


def route_sequence_from_intent(intent: Dict[str, Any]) -> List[str]:
    routes = intent.get("route_sequence")
    if not isinstance(routes, list):
        routes = [intent.get("current_route")]
    return [str(route) for route in routes if str(route or "").strip()]


def build_initial_plan_from_intent(intent: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    routes = route_sequence_from_intent(intent)
    if not routes:
        return None
    first_route = routes[0]
    if not first_route:
        return None
    return {
        "user_intent_summary": str(intent.get("summary") or "受控多路由任务"),
        "decomposition_reason": str(intent.get("reason") or "按受控意图路由执行。"),
        "tasks": [
            {
                "agent_id": first_route,
                "handoff_instruction": _handoff_for_route(first_route, intent),
                "depends_on": None,
            }
        ],
        "finalize_after_this_batch": len(routes) <= 1,
        "routed_by": "controlled_intent",
        "controlled_intent": intent,
    }


def build_next_plan_from_intent(
    intent: Dict[str, Any],
    *,
    completed_agents: List[str],
) -> Optional[Dict[str, Any]]:
    routes = route_sequence_from_intent(intent)
    for route in routes:
        if route not in completed_agents:
            return {
                "user_intent_summary": str(intent.get("summary") or "继续受控多路由任务"),
                "decomposition_reason": f"Harness 多路由：上一专线完成，继续切换到 {route}。",
                "tasks": [
                    {
                        "agent_id": route,
                        "handoff_instruction": _handoff_for_route(route, intent),
                        "depends_on": None,
                    }
                ],
                "finalize_after_this_batch": route == routes[-1],
                "routed_by": "harness",
                "controlled_intent": intent,
            }
    return None


def _latest_user_text(messages: List[Dict[str, str]]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user":
            return str(message.get("content") or "").strip()
    return ""


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    lower = text.lower()
    return any(keyword in text or keyword.lower() in lower for keyword in keywords)


def _wants_decision(text: str, *, wants_query: bool, wants_viz: bool) -> bool:
    if _contains_any(text, _DECISION_STRONG_KEYWORDS):
        return True
    if _DECISION_ADVICE_KEYWORD not in text:
        return False
    if wants_viz and not wants_query:
        return False
    return True


def _intent_type(routes: List[str], *, wants_decision: bool, wants_viz: bool) -> str:
    if routes and routes[0] == "upload_analyst":
        return "upload_then_analyze" if not wants_viz else "upload_then_viz"
    if wants_decision and wants_viz:
        return "query_then_decide_then_viz"
    if wants_decision:
        return "query_then_decide"
    if wants_viz:
        return "query_then_viz"
    if routes and routes[0] == "period_compare":
        return "period_compare"
    return "query_only"


def _final_outputs(*, wants_decision: bool, wants_viz: bool) -> List[str]:
    outputs = ["answer"]
    if wants_decision:
        outputs.append("advice")
    if wants_viz:
        outputs.append("visual")
    return outputs


def _summary(intent_type: str, routes: List[str]) -> str:
    labels = {
        "query_then_decide": "先问数再给经营建议",
        "query_then_viz": "先问数再生成图表",
        "query_then_decide_then_viz": "先问数，再给经营建议，并补充可视化",
        "upload_then_analyze": "上传数据分析",
        "upload_then_viz": "上传数据分析后生成图表或看板",
        "period_compare": "跨期对比分析",
        "query_only": "演示库问数",
    }
    return labels.get(intent_type) or " -> ".join(routes)


def _handoff_for_route(route: str, intent: Dict[str, Any]) -> str:
    user_text = str(intent.get("primary_text") or "").strip()
    if route == "demo_query":
        return f"围绕用户原始需求执行演示库问数，优先保留时间、区域、指标等约束：{user_text}"
    if route == "business_advisor":
        return (
            "基于前置结构化结果生成经营建议，必须引用已有事实，不要重复问数；"
            f"用户原始目标：{user_text}"
        )
    if route == "viz_board":
        return "基于前置结构化结果生成图表或看板方案，不要重新取数；" f"用户原始目标：{user_text}"
    if route == "upload_analyst":
        return f"围绕上传文件或采纳指标执行上传分析：{user_text}"
    if route == "period_compare":
        return f"围绕用户原始需求执行跨期对比分析：{user_text}"
    return user_text
