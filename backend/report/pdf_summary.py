"""LLM or heuristic summary for PDF export."""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List

from backend.config import settings


def _pdf_summary_disabled() -> bool:
    v = os.getenv("CHATBI_PDF_SUMMARY_DISABLED", "").strip().lower()
    return v in ("1", "true", "yes", "on")


def _format_transcript(messages: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    for msg in messages:
        role = str(msg.get("role") or "")
        if role not in ("user", "assistant"):
            continue
        label = "用户" if role == "user" else "助手"
        content = str(msg.get("content") or "").strip()
        if not content:
            continue
        lines.append(f"{label}: {content}")
    return "\n".join(lines)


def _fallback_summary(messages: List[Dict[str, Any]]) -> str:
    users = [str(m.get("content") or "").strip() for m in messages if m.get("role") == "user"]
    assistants = [
        str(m.get("content") or "").strip()
        for m in messages
        if m.get("role") == "assistant"
    ]
    parts: List[str] = ["【会话摘要（离线/降级）】"]
    if users:
        first = users[0][:400]
        parts.append(f"首问：{first}")
        if len(users) > 1:
            parts.append(f"（共 {len(users)} 轮用户提问）")
    if assistants:
        last = assistants[-1]
        if len(last) > 1200:
            last = last[:1200] + "…"
        parts.append(f"最近助手结论：{last}")
    return "\n\n".join(parts)


def summarize_session_for_pdf(messages: List[Dict[str, Any]]) -> str:
    """精炼会话要点，供 PDF 正文使用。"""
    if _pdf_summary_disabled():
        return _fallback_summary(messages)
    transcript = _format_transcript(messages)
    if not transcript.strip():
        return "（无可摘要内容）"

    try:
        from litellm import completion

        params = {
            **settings.llm_params,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是 ChatBI 报告编辑。根据下方对话整理成简洁的中文要点，"
                        "突出数据结论与业务建议，不要逐句复述聊天。"
                        "允许使用分级标题（##）与项目符号。不要编造对话中不存在的数据。"
                    ),
                },
                {
                    "role": "user",
                    "content": f"请基于以下对话写摘要报告：\n\n{transcript}",
                },
            ],
            "temperature": 0.3,
        }
        resp = completion(**params)
        text = _completion_content(resp)
        if text:
            return _markdownish_to_plain_paragraphs(text)
        return _fallback_summary(messages)
    except Exception:
        return _fallback_summary(messages)


def _completion_content(resp: Any) -> str:
    choice = getattr(resp, "choices", None)
    if not choice:
        return ""
    c0 = choice[0]
    if isinstance(c0, dict):
        msg = c0.get("message") or {}
        if isinstance(msg, dict):
            return str(msg.get("content") or "").strip()
    msg = getattr(c0, "message", None)
    if msg is not None:
        return str(getattr(msg, "content", "") or "").strip()
    return ""


def _markdownish_to_plain_paragraphs(text: str) -> str:
    """Strip minimal markdown so PDF shows readable plain structure."""
    t = text.replace("\r\n", "\n")
    t = re.sub(r"^#+\s*", "", t, flags=re.MULTILINE)
    return t.strip()
