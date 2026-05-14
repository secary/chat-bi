"""Inject upload file paths into follow-up turns so the agent does not fall back to DB query."""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any, Dict, List, Optional

# Server-side uploads from POST /upload (see backend/main.py UPLOAD_DIR).
_UPLOAD_PATH_RE = re.compile(
    r"/tmp/chatbi-uploads/[A-Za-z0-9._-]+",
    re.IGNORECASE,
)

# File data cache: keyed by upload path, stores the full skill result with rows
_file_data_cache: Dict[str, Dict[str, Any]] = {}

# Last user message looks like continued work on an uploaded file (not a pure demo-DB question).
_FOLLOWUP_MARKERS = (
    "csv",
    "CSV",
    "上传",
    "附件",
    "该文件",
    "这份",
    "我上传",
    "本地文件",
    "文件里",
    "文件中",
    "表格文件",
    "excel",
    "xlsx",
    "xlsm",
)


def _primary_upload_path(messages: List[Dict[str, str]]) -> str | None:
    """Return the last upload path mention in chronological order (most recent)."""
    last: str | None = None
    for msg in messages:
        if msg.get("role") != "user":
            continue
        text = str(msg.get("content") or "")
        for m in _UPLOAD_PATH_RE.finditer(text):
            last = m.group(0)
    return last


def _should_hint_followup(last_user: str, has_paths: bool) -> bool:
    if not has_paths or not last_user.strip():
        return False
    if any(k in last_user for k in _FOLLOWUP_MARKERS):
        return True
    # 画图 / 展示 without naming "CSV" — still often means the uploaded sheet in short follow-ups.
    if any(
        k in last_user
        for k in ("画图", "图表", "可视化", "展示数据", "有哪些列", "什么数据", "字段")
    ):
        return True
    return False


def augment_messages_for_upload_followup(
    messages: List[Dict[str, str]],
) -> List[Dict[str, str]]:
    """Prepend a factual hint to the latest user turn when a prior turn referenced an upload path.

    This keeps ReAct from routing generic phrases like "帮我分析并画图" to `chatbi-semantic-query`
    when the user clearly continues work on an uploaded CSV/XLSX.
    """
    if not messages:
        return messages

    primary = _primary_upload_path(messages)
    if not primary:
        return messages

    last_idx = None
    for i in range(len(messages) - 1, -1, -1):
        if messages[i].get("role") == "user":
            last_idx = i
            break
    if last_idx is None:
        return messages

    last_content = str(messages[last_idx].get("content") or "")
    if primary in last_content:
        return messages
    if not _should_hint_followup(last_content, True):
        return messages

    hint = (
        "[ChatBI 上下文：本会话中用户曾上传的数据文件路径为："
        f"{primary}。若当前问题针对该上传文件进行分析、汇总或画图，"
        "必须先调用「chatbi-file-ingestion」并传入该路径；需要完整行数据或可视化时请附加参数 --include-rows。"
        "重要：已读取的文件数据会在本会话中缓存，后续分析应直接使用缓存数据（rows 字段）进行计算，"
        "除非明确需要刷新数据，否则不要重复调用 chatbi-file-ingestion 读取同一文件。"
        "不要用「chatbi-semantic-query」查询演示数据库来代替该文件内容。]\n\n"
    )

    out = deepcopy(messages)
    u = dict(out[last_idx])
    u["content"] = hint + last_content
    out[last_idx] = u
    return out


def cache_file_data(upload_path: str, data: Dict[str, Any]) -> None:
    """Cache the full skill result for an uploaded file path."""
    _file_data_cache[upload_path] = data


def get_cached_file_data(upload_path: str) -> Optional[Dict[str, Any]]:
    """Return cached data for an upload path, or None if not yet cached."""
    return _file_data_cache.get(upload_path)


def get_cached_rows(upload_path: str) -> List[Dict[str, Any]]:
    """Return cached rows (full data) for an upload path, or empty list."""
    cached = get_cached_file_data(upload_path)
    if not cached:
        return []
    data = cached.get("data", {})
    if isinstance(data, dict):
        rows = data.get("rows")
        if isinstance(rows, list) and rows:
            return rows
    return []
