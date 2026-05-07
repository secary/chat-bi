"""LLM JSON router: selects specialist agent ids for multi-agent mode."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from litellm import acompletion

from backend.agent.multi_agent_registry import list_registry_agent_ids
from backend.agent.planner import parse_json_object
from backend.app_llm import effective_llm_params
from backend.trace import log_event


def _router_system_prompt() -> str:
    ids = list_registry_agent_ids()
    lines = "\n".join(f"- `{a}`" for a in ids)
    return f"""你是 ChatBI 多专线编排路由。根据用户最新需求，选择需要参与回答的专线（可多个，顺序有意义）。
registry 内专线 id 只能是：{",".join(ids) if ids else "（空）"}

## 输出 JSON（仅此一个对象）
{{
  "agents": ["专线id", ...],
  "user_intent_summary": "一句话概括用户意图",
  "routing_reason": "为何选择这些专线"
}}

规则：
- agents 数组最多 2 个专线 id（必须来自上表）
- 若只需通用分析，优先选择 `analysis`
- 若涉及合规、风险、授信 interpretation，包含 `risk`
- 若涉及渠道、客群、营销增长，包含 `marketing`
- 不要输出 Markdown 围栏"""


async def call_route_llm(
    messages: List[Dict[str, str]],
    trace_id: str = "",
) -> Optional[Dict[str, Any]]:
    """Returns parsed router JSON or None on failure."""
    user_tail = ""
    if messages:
        user_tail = messages[-1].get("content") or ""
    llm_messages = [
        {"role": "system", "content": _router_system_prompt()},
        {
            "role": "user",
            "content": f"用户对话末尾最新输入如下，请路由：\n{user_tail}",
        },
    ]
    try:
        resp = await acompletion(
            **effective_llm_params(),
            messages=llm_messages,
            response_format={"type": "json_object"},
            temperature=0.1,
        )
    except Exception as exc:
        log_event(
            trace_id,
            "agent.multi_route",
            "failed",
            str(exc),
            level="WARN",
        )
        return None
    content = resp.choices[0].message.content
    if not content:
        return None
    try:
        return parse_json_object(content)
    except (json.JSONDecodeError, ValueError):
        log_event(
            trace_id,
            "agent.multi_route",
            "parse_failed",
            content[:200],
            level="WARN",
        )
        return None
