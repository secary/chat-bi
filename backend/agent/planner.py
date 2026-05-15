from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from backend.llm_runtime import chatbi_acompletion

"""
Each ReAct round, tell LLM should return "action", such as skill/finish/answer/done...
"""


async def call_llm_for_react_step(
    system_prompt: str, messages: List[Dict[str, str]]
) -> Optional[Dict[str, Any]]:
    llm_messages = [
        {"role": "system", "content": system_prompt},
        *messages,
        {
            "role": "user",
            "content": "请只输出一个 JSON 对象作为本步决策（必须包含 action 字段），不要输出其它文字。",
        },
    ]

    try:
        resp = await chatbi_acompletion(
            messages=llm_messages,
            response_format={"type": "json_object"},
            temperature=0.1,
        )
    except Exception as exc:
        raise RuntimeError(f"LLM 调用失败：{type(exc).__name__}: {exc}") from exc

    content = resp.choices[0].message.content
    if content is None or not str(content).strip():
        return None
    try:
        return parse_json_object(content)
    except (json.JSONDecodeError, ValueError):
        return None


"""
用于stream_chat_legacy中，默认不使用。
"""


async def call_llm_for_plan(
    system_prompt: str, messages: List[Dict[str, str]]
) -> Optional[Dict[str, Any]]:
    llm_messages = [
        {"role": "system", "content": system_prompt},
        *messages,
        {"role": "user", "content": "请以 JSON 格式输出你的行动计划。"},
    ]

    try:
        resp = await chatbi_acompletion(
            messages=llm_messages,
            response_format={"type": "json_object"},
            temperature=0.1,
        )
    except Exception as exc:
        raise RuntimeError(f"LLM 调用失败：{type(exc).__name__}: {exc}") from exc

    content = resp.choices[0].message.content
    if content is None or not str(content).strip():
        return None
    try:
        return parse_json_object(content)
    except (json.JSONDecodeError, ValueError):
        return None


def parse_json_object(content: str) -> Dict[str, Any]:
    text = content.strip()
    if not text:
        raise ValueError("empty JSON content")
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()
    decoder = json.JSONDecoder()
    obj, _end = decoder.raw_decode(text)
    if not isinstance(obj, dict):
        raise ValueError("JSON root must be an object")
    return obj
