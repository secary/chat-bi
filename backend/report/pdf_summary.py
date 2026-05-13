"""LLM or heuristic summary for PDF export."""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List

from backend.llm_runtime import chatbi_completion


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
        str(m.get("content") or "").strip() for m in messages if m.get("role") == "assistant"
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
        resp = chatbi_completion(
            messages=[
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
            temperature=0.3,
        )
        text = _completion_content(resp)
        if text:
            return _markdown_to_html(text)
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


def _markdown_to_html(text: str) -> str:
    """将 LLM 返回的 markdown 转换为可用于 PDF 的 HTML（仅处理常用格式）。"""
    lines = text.split("\n")
    in_ul = False
    result: list[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]
        # 跳过分隔行（如 |---|）
        if re.match(r"^\|[-: |]+\|$", line) or re.match(r"^\|?\s*[-:]+\s*[-:|\s]*\|?$", line):
            i += 1
            continue
        # h2 / h3 标题
        m = re.match(r"^(#{2,3})\s+(.+)$", line)
        if m:
            if in_ul:
                result.append("</ul>")
                in_ul = False
            level = len(m.group(1))
            content = _process_inline_markdown(m.group(2))
            result.append(f"<h{level}>{content}</h{level}>")
            i += 1
            continue
        # 列表项
        m = re.match(r"^[-*]\s+(.+)$", line)
        if m:
            if not in_ul:
                result.append("<ul>")
                in_ul = True
            content = _process_inline_markdown(m.group(1))
            result.append(f"<li>{content}</li>")
            i += 1
            continue
        # 关闭未关闭的 ul
        if in_ul:
            result.append("</ul>")
            in_ul = False
        # 空行处理
        if line.strip() == "":
            i += 1
            continue
        # 普通段落
        content = _process_inline_markdown(line)
        result.append(f"<p>{content}</p>")
        i += 1

    if in_ul:
        result.append("</ul>")
    return "\n".join(result)


def _process_inline_markdown(text: str) -> str:
    """处理行内 markdown：加粗 **text** -> <strong>text</strong>"""
    # 先处理加粗
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    # 处理斜体（可选）
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    return text
