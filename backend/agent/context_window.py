"""Sliding window + summary injection for multi-turn conversation context management.

This module provides context management that builds a hybrid context consisting of:
1. Recent N turns of conversation
2. Relevant historical segments retrieved based on the current query
3. Session summary

The approach is based on MemGPT-style context paging and LangChain's ConversationalRetrievalChain.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

from backend.memory_repo import list_recent_session_summaries
from backend.session_repo import list_messages_for_llm

_UPLOAD_PATH_RE = re.compile(r"/tmp/chatbi-uploads/[A-Za-z0-9._-]+", re.IGNORECASE)

# Keywords that indicate skill-related context should be preserved
_SKILL_CONTEXT_KEYWORDS = (
    "skill",
    "技能",
    "指标",
    "查询",
    "数据库",
    "表",
    "概览",
    "语义",
    "上传",
    "文件",
    "采纳",
    "分析",
    "图表",
    "看板",
    "dashboard",
)


class ConversationContextBuilder:
    """
    Builds hybrid context for LLM using sliding window + summary injection.

    Reduces interference from irrelevant history and keeps skill metadata
    stable in the model's active context window.
    """

    def __init__(
        self,
        max_recent_turns: int = 10,
        max_summary_chars: int = 2000,
        max_retrieved_chars: int = 1500,
    ):
        """
        Args:
            max_recent_turns: Number of recent conversation turns to include
            max_summary_chars: Maximum characters for session summary
            max_retrieved_chars: Maximum characters for retrieved relevant segments
        """
        self.max_recent_turns = max_recent_turns
        self.max_summary_chars = max_summary_chars
        self.max_retrieved_chars = max_retrieved_chars

    def build_context(
        self,
        session_id: Optional[int],
        current_query: str,
        all_messages: Optional[List[dict]] = None,
    ) -> str:
        """
        Build hybrid context for the current query.

        Args:
            session_id: The chat session ID (optional)
            current_query: The current user query (used for relevance retrieval)
            all_messages: Pre-loaded messages (if None and session_id provided, loads from DB)

        Returns:
            A string containing the hybrid context:
            [Session Summary]\n\n[Recent Turns]\n\n[Relevant Historical Segments]
        """
        parts: List[str] = []

        if session_id:
            session_summary = self._get_session_summary(session_id)
            if session_summary:
                parts.append(f"## 会话摘要\n{session_summary}")

        if all_messages is not None:
            recent_turns = self._format_recent_turns(all_messages)
            if recent_turns:
                parts.append(f"## 最近对话\n{recent_turns}")

            relevant_history = self._retrieve_relevant_history(current_query, all_messages)
            if relevant_history:
                parts.append(f"## 相关历史\n{relevant_history}")
        elif session_id:
            recent_turns = self._get_recent_turns(session_id)
            if recent_turns:
                parts.append(f"## 最近对话\n{recent_turns}")

        return "\n\n".join(parts)

    def build_context_for_react(
        self,
        session_id: Optional[int],
        current_query: str,
        all_messages: List[dict],
    ) -> str:
        """
        Build context specifically for ReAct agent loop.
        Unlike multi-agent manager, ReAct agent needs full message list
        because it maintains its own working list.
        """
        session_summary = ""
        if session_id:
            session_summary = self._get_session_summary(session_id)
        recent_turns = self._format_recent_turns(all_messages)

        parts: List[str] = []
        if session_summary:
            parts.append(f"## 会话摘要\n{session_summary}")
        if recent_turns:
            parts.append(f"## 对话历史\n{recent_turns}")

        return "\n\n".join(parts)

    def _get_session_summary(self, session_id: int) -> str:
        """Get the most recent session summary for this session."""
        try:
            summaries = list_recent_session_summaries(user_id=0, limit=10)
            for s in summaries:
                if s.get("source_session_id") == session_id:
                    content = str(s.get("content") or "")[: self.max_summary_chars]
                    if content:
                        return content
        except Exception:
            pass
        return ""

    def _get_recent_turns(self, session_id: int) -> str:
        """Get recent conversation turns from DB."""
        messages = list_messages_for_llm(session_id, self.max_recent_turns * 2)
        return self._format_recent_turns(messages)

    def _format_recent_turns(self, messages: List[dict]) -> str:
        """Format messages as a conversation string."""
        if not messages:
            return ""

        lines: List[str] = []
        for m in messages[-self.max_recent_turns * 2 :]:
            role = str(m.get("role") or "")
            content = str(m.get("content") or "").strip()
            if content and role in ("user", "assistant"):
                if len(content) > 500:
                    content = content[:500] + "..."
                lines.append(f"{role}: {content}")

        return "\n".join(lines)

    def _retrieve_relevant_history(
        self,
        current_query: str,
        all_messages: List[dict],
    ) -> str:
        """
        Retrieve historically relevant segments based on current query.
        Uses keyword matching to find relevant context from earlier turns.
        """
        if len(all_messages) <= self.max_recent_turns * 2:
            return ""

        query_keywords = self._extract_keywords(current_query)
        if not query_keywords:
            return ""

        relevant_segments: List[Tuple[str, str]] = []

        for m in all_messages[: -self.max_recent_turns * 2]:
            content = str(m.get("content") or "").strip()
            if not content or len(content) < 20:
                continue

            role = str(m.get("role") or "")
            if role not in ("user", "assistant"):
                continue

            if self._is_relevant_segment(content, query_keywords):
                if len(content) > 300:
                    content = content[:300] + "..."
                relevant_segments.append((role, content))

        if not relevant_segments:
            return ""

        lines: List[str] = []
        for role, content in relevant_segments[-5:]:
            lines.append(f"{role}: {content}")

        combined = "\n".join(lines)
        if len(combined) > self.max_retrieved_chars:
            combined = combined[: self.max_retrieved_chars] + "..."

        return combined

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from query for relevance matching."""
        text = text.lower()
        words = re.findall(r"[\w]+", text)
        keywords = [w for w in words if len(w) >= 2]
        for kw in _SKILL_CONTEXT_KEYWORDS:
            if kw in text:
                keywords.append(kw)
        return keywords

    def _is_relevant_segment(self, content: str, keywords: List[str]) -> bool:
        """Check if a content segment is relevant to the query keywords."""
        content_lower = content.lower()
        matches = sum(1 for kw in keywords if kw in content_lower)
        return matches >= min(2, len(keywords))


def build_manager_context(
    session_id: Optional[int],
    current_query: str,
    messages: List[dict],
) -> str:
    """
    Convenience function to build context for Manager LLM.

    Args:
        session_id: The chat session ID (optional)
        current_query: The current user query
        messages: All messages in the conversation

    Returns:
        Hybrid context string for Manager LLM
    """
    builder = ConversationContextBuilder()
    return builder.build_context(session_id, current_query, messages)


def build_react_context(
    session_id: Optional[int],
    current_query: str,
    messages: List[dict],
) -> str:
    """
    Convenience function to build context for ReAct agent.

    Args:
        session_id: The chat session ID (optional)
        current_query: The current user query
        messages: All messages in the conversation

    Returns:
        Hybrid context string for ReAct agent
    """
    builder = ConversationContextBuilder()
    return builder.build_context_for_react(session_id, current_query, messages)
