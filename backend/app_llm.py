"""Merge env-based Settings with optional llm_settings row for LiteLLM."""

from __future__ import annotations

from typing import Any, Dict

from backend.config import settings
from backend.llm_settings_repo import get_row


def effective_llm_params() -> Dict[str, Any]:
    params: Dict[str, Any] = dict(settings.llm_params)
    row = get_row()
    if not row:
        return params
    if row.get("model"):
        params["model"] = str(row["model"])
    if row.get("api_base"):
        params["api_base"] = str(row["api_base"])
    if row.get("api_key"):
        params["api_key"] = str(row["api_key"])
    return params
