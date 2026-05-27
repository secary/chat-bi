"""Resolve whether the current user turn targets demo DB or uploaded files."""

from __future__ import annotations

import re
from enum import Enum
from typing import Dict, List, Optional, Tuple

from backend.agent.executor import latest_user_prompt_for_demo_data_skills

_UPLOAD_PATH_RE = re.compile(r"/tmp/chatbi-uploads/[A-Za-z0-9._-]+", re.IGNORECASE)

_DEMO_DB_EXPLICIT_MARKERS = (
    "不考虑上传",
    "不用上传",
    "无需上传",
    "忽略上传",
    "不要用上传",
    "不要上传",
    "不使用上传",
    "从数据库",
    "查数据库",
    "演示库",
    "演示数据库",
    "业务库",
    "查库",
    "demo库",
    "demo 库",
)

_UPLOAD_FOLLOWUP_MARKERS = (
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
    "采纳",
)

_DEMO_QUERY_BUSINESS_MARKERS = (
    "销售",
    "毛利",
    "利润",
    "营收",
    "收入",
    "趋势",
    "环比",
    "同比",
    "排行",
    "排名",
    "区域",
    "渠道",
    "产品",
    "指标",
    "查询",
    "客户",
    "订单",
)


class DataSourceIntent(str, Enum):
    DEMO_DATABASE = "demo_database"
    UPLOAD_FILE = "upload_file"
    AMBIGUOUS = "ambiguous"


def has_upload_file_reference(text: str) -> bool:
    """True when dialogue text suggests a local uploaded CSV/XLSX path."""
    if not text:
        return False
    low = text.lower()
    if "chatbi-uploads" in low:
        return True
    if "/tmp/" in low and any(ext in low for ext in (".csv", ".xlsx", ".xls")):
        return True
    return False


def current_user_text(messages: List[Dict[str, str]]) -> str:
    return latest_user_prompt_for_demo_data_skills(messages)


def _upload_path_in_text(text: str) -> str:
    if not text:
        return ""
    m = _UPLOAD_PATH_RE.search(text)
    return m.group(0) if m else ""


def _has_demo_db_explicit_signal(text: str) -> bool:
    if not text:
        return False
    low = text.lower()
    return any(m in text or m.lower() in low for m in _DEMO_DB_EXPLICIT_MARKERS)


def _has_upload_followup_signal(text: str) -> bool:
    if not text:
        return False
    if _upload_path_in_text(text):
        return True
    return any(m in text for m in _UPLOAD_FOLLOWUP_MARKERS)


def _is_typical_demo_query(text: str) -> bool:
    if not text:
        return False
    return any(m in text for m in _DEMO_QUERY_BUSINESS_MARKERS)


def _prior_upload_path(messages: List[Dict[str, str]], *, exclude_latest: bool = True) -> str:
    """Last upload path in user messages, optionally skipping the latest user turn."""
    found: List[str] = []
    user_indices = [i for i, m in enumerate(messages) if m.get("role") == "user"]
    if not user_indices:
        return ""
    scan = user_indices[:-1] if exclude_latest and len(user_indices) > 1 else user_indices
    for i in scan:
        content = str(messages[i].get("content") or "")
        p = _upload_path_in_text(content)
        if p:
            found.append(p)
    return found[-1] if found else ""


def _dialogue_blob(messages: List[Dict[str, str]], max_msgs: int = 32) -> str:
    tail = messages[-max_msgs:] if len(messages) > max_msgs else messages
    parts: List[str] = []
    for m in tail:
        c = str(m.get("content") or "").strip()
        if c:
            parts.append(c)
    return "\n".join(parts)


def resolve_data_source(messages: List[Dict[str, str]]) -> DataSourceIntent:
    """
    Infer data source for the **current** user turn (not whole-session upload lock-in).
    """
    text = current_user_text(messages)
    current_path = _upload_path_in_text(text)

    if _has_demo_db_explicit_signal(text):
        return DataSourceIntent.DEMO_DATABASE

    if current_path or (
        _has_upload_followup_signal(text) and not _has_demo_db_explicit_signal(text)
    ):
        return DataSourceIntent.UPLOAD_FILE

    if _is_typical_demo_query(text) and not _has_upload_followup_signal(text):
        return DataSourceIntent.DEMO_DATABASE

    blob = _dialogue_blob(messages)
    if has_upload_file_reference(blob):
        return DataSourceIntent.AMBIGUOUS

    return DataSourceIntent.DEMO_DATABASE


def resolve_data_source_context(
    messages: List[Dict[str, str]],
) -> Tuple[DataSourceIntent, Optional[str], bool]:
    intent = resolve_data_source(messages)
    text = current_user_text(messages)
    current_path = _upload_path_in_text(text) or None
    prior_path = _prior_upload_path(messages) or None
    upload_path = current_path or prior_path
    blob = _dialogue_blob(messages)
    has_prior = bool(prior_path or (has_upload_file_reference(blob) and not current_path))
    return intent, upload_path, has_prior


def format_intent_context_block(
    intent: DataSourceIntent,
    *,
    upload_path: Optional[str] = None,
    has_prior_upload: bool = False,
) -> str:
    lines = ["## 本轮数据源判断（系统解析，选技能时必须对齐）"]
    if intent == DataSourceIntent.DEMO_DATABASE:
        lines.append(
            "- **本轮目标：演示业务库问数**（`chatbi-semantic-query` 等演示库技能）。"
            "即使用户曾在会话中上传过文件，本轮也不要用 `chatbi-file-ingestion` 代替数据库查询。"
        )
    elif intent == DataSourceIntent.UPLOAD_FILE:
        lines.append(
            "- **本轮目标：用户上传文件或其延续分析**（`chatbi-file-ingestion` / `chatbi-auto-analysis`）。"
            "不要用 `chatbi-semantic-query` 查询演示库来代替文件内容。"
        )
        if upload_path:
            lines.append(f"- 关联上传路径：`{upload_path}`")
    else:
        lines.append(
            "- **本轮数据源待你结合上下文判断**：若用户仍在说上传表/附件/采纳/画图，走上传技能；"
            "若用户在问区域/销售额/趋势等业务库指标且未指向文件，走演示库 `chatbi-semantic-query`。"
        )
        if has_prior_upload and upload_path:
            lines.append(
                f"- 会话中曾出现上传路径：`{upload_path}`（仅供参考，不以历史路径单独决定本轮）。"
            )
    return "\n".join(lines)


def format_handoff_data_source_line(intent: DataSourceIntent) -> str:
    if intent == DataSourceIntent.DEMO_DATABASE:
        return "【本轮数据源】演示业务库（查演示库，勿用历史上传文件代替）"
    if intent == DataSourceIntent.UPLOAD_FILE:
        return "【本轮数据源】上传文件延续（分析/采纳上传表）"
    return "【本轮数据源】待判断（请根据【用户原述】判断查上传表还是演示库）"
