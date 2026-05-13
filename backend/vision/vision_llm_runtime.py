"""LiteLLM calls for image/table extraction using a single vision-capable profile."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from backend.app_llm import effective_llm_params, profile_row_to_litellm_params
from backend import llm_profile_repo
from backend.llm_settings_repo import get_row


def is_vision_disabled_by_env() -> bool:
    v = os.getenv("CHATBI_VISION_DISABLED", "").strip().lower()
    return v in ("1", "true", "yes", "on")


def _vision_allow_env_main() -> bool:
    v = os.getenv("CHATBI_VISION_ALLOW_ENV_MAIN", "").strip().lower()
    return v in ("1", "true", "yes", "on")


def resolve_vision_litellm_base_params() -> Optional[Dict[str, Any]]:
    """Return merged LiteLLM kwargs for exactly one vision call, or None if unavailable."""
    if is_vision_disabled_by_env():
        return None
    settings_row = get_row()
    if settings_row:
        vpid = settings_row.get("vision_profile_id")
        if vpid is not None:
            row = llm_profile_repo.get_by_id(int(vpid))
            if row:
                return profile_row_to_litellm_params(row)
        aid = settings_row.get("active_profile_id")
        if aid is not None:
            active = llm_profile_repo.get_by_id(int(aid))
            if active and int(active.get("supports_vision") or 0):
                return profile_row_to_litellm_params(active)
    if _vision_allow_env_main():
        p = effective_llm_params()
        if p.get("model"):
            return p
    return None


def compute_vision_extract_enabled() -> bool:
    return resolve_vision_litellm_base_params() is not None


async def vision_acompletion(**kwargs: Any) -> Any:
    from litellm import acompletion

    base = resolve_vision_litellm_base_params()
    if not base:
        raise RuntimeError("vision_unavailable")
    merged = {**base, **kwargs}
    merged.pop("response_format", None)
    return await acompletion(**merged)
