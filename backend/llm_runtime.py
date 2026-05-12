"""LiteLLM calls with multi-profile fallback."""

# Auto fallback to other llm model if one model is not available.
from __future__ import annotations

import logging
from typing import Any, Dict, List

from backend.app_llm import effective_llm_params, profile_row_to_litellm_params
from backend import llm_profile_repo
from backend.llm_settings_repo import get_row

logger = logging.getLogger(__name__)


def _profile_chain_rows() -> List[Dict[str, Any]]:
    rows = llm_profile_repo.list_ordered()
    if not rows:
        return []
    settings_row = get_row()
    aid = settings_row.get("active_profile_id") if settings_row else None
    if not aid:
        return rows
    active = llm_profile_repo.get_by_id(int(aid))
    if not active:
        return rows
    rid = int(active["id"])
    others = [r for r in rows if int(r["id"]) != rid]
    return [active] + others


def _attempt_param_dicts() -> List[Dict[str, Any]]:
    chain = _profile_chain_rows()
    if chain:
        return [profile_row_to_litellm_params(r) for r in chain]
    return [effective_llm_params()]


def _should_try_fallback(exc: BaseException) -> bool:
    name = type(exc).__name__
    if name in (
        "APIConnectionError",
        "APIError",
        "Timeout",
        "OpenAITimeoutError",
        "RateLimitError",
        "InternalServerError",
        "ServiceUnavailableError",
        "AuthenticationError",
        "ConnectionError",
        "TimeoutError",
    ):
        return True
    low = str(exc).lower()
    for token in (
        "timeout",
        "connection refused",
        "rate limit",
        "503",
        "502",
        "429",
        "401",
        "403",
    ):
        if token in low:
            return True
    return False


async def chatbi_acompletion(**kwargs: Any) -> Any:
    from litellm import acompletion

    attempts = _attempt_param_dicts()
    for i, base in enumerate(attempts):
        merged = {**base, **kwargs}
        merged.pop("response_format", None)
        try:
            return await acompletion(**merged)
        except Exception as exc:
            if i < len(attempts) - 1 and _should_try_fallback(exc):
                logger.warning("chatbi_acompletion fallback after %s", type(exc).__name__)
                continue
            raise
    raise RuntimeError("chatbi_acompletion: no attempts")


def chatbi_completion(**kwargs: Any) -> Any:
    from litellm import completion

    attempts = _attempt_param_dicts()
    for i, base in enumerate(attempts):
        merged = {**base, **kwargs}
        merged.pop("response_format", None)
        try:
            return completion(**merged)
        except Exception as exc:
            if i < len(attempts) - 1 and _should_try_fallback(exc):
                logger.warning("chatbi_completion fallback after %s", type(exc).__name__)
                continue
            raise
    raise RuntimeError("chatbi_completion: no attempts")
