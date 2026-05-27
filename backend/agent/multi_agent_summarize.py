"""Summarizer LLM: merges specialist observations into one user-facing answer."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from backend.agent.abort_async import ChatAbortedError, await_with_abort
from backend.agent.planner import parse_json_object
from backend.llm_runtime import chatbi_acompletion
from backend.trace import log_event

SUMMARY_SYSTEM = """你是 ChatBI 的最终回答生成器：综合多个执行结果，向用户输出一份连贯、可执行的 Markdown 最终答复。

规则：
- 仅基于用户问题与 results[].observation 组织语言；禁止编造未出现的数字
- 如果提供 fact_ledger，它是事实白名单：最终回答中的数字、对象、建议依据必须能回到 fact_ledger 或 results[].observation
- 对没有事实依据的建议必须明确写成“暂无足够事实支撑”，不要补全或猜测
- 同一结果的 observation 可能含多段「第 N 次 · skill」工具摘要，须全部纳入最终答复，禁止只写最后一段
- 面向业务用户回答，不要暴露内部执行线、agent id、skill 名、handoff_instruction、Observation 等工程字段
- 禁止输出“查询专线”“执行线”“专线”“agent”“skill”等内部链路说明
- 结构清晰：可先总述，再按业务主题分点；必要时用列表
- 输出 JSON（仅此一个对象）：
{
  "text": "给用户的完整 Markdown 正文",
  "chart_plan": null,
  "kpi_cards": []
}
- chart_plan / kpi_cards 通常填 null / []（最终图表由系统根据全部工具执行结果渲染）；除非 Observation 明确支持且你需要强调单一图表结构时可填写与单次模式相同字段"""


async def call_summarize_llm(
    user_question: str,
    blocks: List[Dict[str, str]],
    trace_id: str = "",
    fact_ledger: str = "",
) -> Optional[Dict[str, Any]]:
    """Summarize result blocks without exposing internal route metadata."""
    body = json.dumps(
        {
            "user_question": user_question,
            "fact_ledger": fact_ledger,
            "results": _public_result_blocks(blocks),
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


def _public_result_blocks(blocks: List[Dict[str, str]]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for idx, block in enumerate(blocks, start=1):
        observation = str(block.get("observation") or "").strip()
        if not observation:
            continue
        out.append(
            {
                "result_no": str(idx),
                "observation": observation,
            }
        )
    return out
