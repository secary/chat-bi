"""Summarizer LLM: merges specialist observations into one user-facing answer."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from litellm import acompletion

from backend.agent.planner import parse_json_object
from backend.app_llm import effective_llm_params
from backend.trace import log_event

SUMMARY_SYSTEM = """你是 ChatBI「汇总专线」：综合多条专线工具返回的 Observation 摘要，生成一份连贯、可执行的 Markdown 回答。

规则：
- 仅基于提供的 Observation 与用户问题组织语言，禁止编造未出现的数字
- 结构清晰：可先总述，再分专线要点；必要时用列表
- 输出 JSON（仅此一个对象）：
{
  "text": "给用户的完整 Markdown 正文",
  "chart_plan": null,
  "kpi_cards": []
}
- chart_plan / kpi_cards 通常填 null / []（最终图表由系统根据最后一次工具结果渲染）；除非 Observation 明确支持且你需要强调单一图表结构时可填写与单次模式相同字段"""


async def call_summarize_llm(
    user_question: str,
    blocks: List[Dict[str, str]],
    trace_id: str = "",
) -> Optional[Dict[str, Any]]:
    """blocks: items with keys agent, label, observation."""
    body = json.dumps(
        {
            "user_question": user_question,
            "specialists": blocks,
        },
        ensure_ascii=False,
    )
    llm_messages = [
        {"role": "system", "content": SUMMARY_SYSTEM},
        {"role": "user", "content": body},
    ]
    try:
        resp = await acompletion(
            **effective_llm_params(),
            messages=llm_messages,
            response_format={"type": "json_object"},
            temperature=0.2,
        )
    except Exception as exc:
        log_event(
            trace_id,
            "agent.multi_summary",
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
        return None
