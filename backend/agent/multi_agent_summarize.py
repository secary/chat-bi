"""Summarizer LLM: merges specialist observations into one user-facing answer."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from backend.agent.abort_async import ChatAbortedError, await_with_abort
from backend.agent.planner import parse_json_object
from backend.llm_runtime import chatbi_acompletion
from backend.trace import log_event

SUMMARY_SYSTEM = """你是 ChatBI 多专线的 **Manager**：综合各子任务专线返回的 Observation 摘要，向用户输出一份连贯、可执行的 Markdown 最终答复。

规则：
- 仅基于各子任务的「交办说明 handoff_instruction」与 Observation、以及用户问题组织语言；禁止编造未出现的数字
- 结构清晰：可先总述，再按子任务或专线分点；必要时用列表
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
    """blocks: items with keys agent, label, observation, handoff_instruction (optional)."""
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
        resp = await await_with_abort(
            chatbi_acompletion(
                messages=llm_messages,
                response_format={"type": "json_object"},
                temperature=0.2,
            ),
            trace_id,
        )
    except ChatAbortedError:
        raise
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
