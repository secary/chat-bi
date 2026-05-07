"""LLM-based memory refresh and prompt formatting."""

from __future__ import annotations

import os
import re
from typing import List

from litellm import acompletion

from backend.app_llm import effective_llm_params
from backend.memory_repo import (
    get_long_term_row,
    insert_session_summary,
    list_recent_session_summaries,
    trim_session_summaries,
    upsert_long_term,
)
from backend.trace import log_event

_MEMORY_OFF = os.getenv("CHATBI_MEMORY_DISABLED", "").strip().lower() in (
    "1",
    "true",
    "yes",
)


def _title_from_user_message(message: str) -> str:
    collapsed = re.sub(r"\s+", " ", message).strip()
    return (collapsed[:80] or "对话摘要")


def format_memory_for_prompt(user_id: int) -> str:
    if _MEMORY_OFF:
        return ""
    row = get_long_term_row(user_id)
    summaries = list_recent_session_summaries(user_id, 5)
    parts: List[str] = []
    if row and str(row.get("content") or "").strip():
        parts.append("## 长期偏好与习惯\n" + str(row["content"])[:2000])
    if summaries:
        lines: List[str] = []
        for s in summaries:
            title = s.get("title") or "会话"
            body = str(s.get("content") or "")[:500]
            lines.append(f"- **{title}**：{body}")
        parts.append("## 近期会话摘要\n" + "\n".join(lines))
    if not parts:
        return ""
    return (
        "\n\n".join(parts)
        + "\n\n（以上为用户侧记忆，仅作风格与意图参考，业务数据以工具查询结果为准。）\n"
    )


async def _llm_text(system: str, user: str) -> str:
    resp = await acompletion(
        **effective_llm_params(),
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
        max_tokens=1024,
    )
    text = (resp.choices[0].message.content or "").strip()
    return text


async def refresh_memory_after_turn(
    trace_id: str,
    user_id: int,
    session_id: int,
    user_message: str,
    assistant_text: str,
) -> None:
    if _MEMORY_OFF:
        return
    try:
        summary = await _llm_text(
            "你是 BI 助手记忆模块。用中文写一段不超过 400 字的会话摘要，"
            "突出用户关心的指标、维度、时间范围与结论，不要编造数字。",
            f"用户问题：{user_message[:2000]}\n\n助手回答摘录：{assistant_text[:6000]}",
        )
        if not summary:
            return
        title = _title_from_user_message(user_message)
        insert_session_summary(user_id, session_id, title, summary[:8000])
        trim_session_summaries(user_id, 30)

        summaries = list_recent_session_summaries(user_id, 15)
        blob = "\n---\n".join(
            f"{s.get('title') or ''}: {str(s.get('content') or '')[:600]}" for s in summaries
        )
        prior = get_long_term_row(user_id)
        prior_txt = str(prior.get("content") or "")[:4000] if prior else ""
        merged = await _llm_text(
            "你是记忆整理器。将「近期会话摘要」与「旧长期记忆」合并为一段不超过 1200 字"
            "的中文「用户查询习惯与稳定偏好」，去除重复，保留可复用的分析口径偏好；不要编造业务数字。",
            f"旧长期记忆：\n{prior_txt}\n\n近期会话摘要：\n{blob[:12000]}",
        )
        if merged:
            upsert_long_term(user_id, merged[:12000])
    except Exception as exc:
        log_event(
            trace_id,
            "memory.service",
            "refresh_failed",
            str(exc),
            level="WARN",
        )
