"""Message shaping for multi-agent Manager subtasks."""

from __future__ import annotations

from typing import Dict, List, Optional

from backend.agent.data_source_intent import (
    DataSourceIntent,
    format_handoff_data_source_line,
    resolve_data_source,
)


def build_subtask_messages(
    messages: List[Dict[str, str]],
    handoff_instruction: str,
    prior_observation: Optional[str] = None,
    *,
    data_source_intent: Optional[DataSourceIntent] = None,
) -> List[Dict[str, str]]:
    """
    Keeps prior dialogue; replaces the last user turn with Manager 交办 + 用户原述
    (+ optional dependency observation summary).
    """
    latest_user = ""
    last_user_idx = -1
    for i in range(len(messages) - 1, -1, -1):
        if messages[i].get("role") == "user":
            latest_user = str(messages[i].get("content") or "")
            last_user_idx = i
            break
    intent = data_source_intent if data_source_intent is not None else resolve_data_source(messages)
    parts: List[str] = [format_handoff_data_source_line(intent)]
    parts.append(f"【Manager 交办】\n{handoff_instruction.strip()}")
    if prior_observation and prior_observation.strip():
        parts.append(f"【前置子任务结果摘要】\n{prior_observation.strip()}")
    parts.append(f"【用户原述】\n{latest_user.strip()}")
    composed = "\n\n".join(parts)
    out: List[Dict[str, str]] = [dict(m) for m in messages]
    if last_user_idx >= 0:
        out[last_user_idx] = {**out[last_user_idx], "content": composed}
    return out
