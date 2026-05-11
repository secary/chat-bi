"""Merge env-based Settings with optional llm_settings / llm_model_profile for LiteLLM."""

from __future__ import annotations

from typing import Any, Dict

from backend.config import settings
from backend import llm_profile_repo
from backend.llm_settings_repo import get_row


def _overlay_saved_row(params: Dict[str, Any], row: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(params)
    if row.get("model"):
        out["model"] = str(row["model"])
    if row.get("api_base"):
        out["api_base"] = str(row["api_base"])
    if row.get("api_key"):
        out["api_key"] = str(row["api_key"])
    return out


def effective_llm_params() -> Dict[str, Any]:
    params: Dict[str, Any] = dict(settings.llm_params)
    row = get_row()
    if not row:
        return params
    aid = row.get("active_profile_id")
    if aid:
        prof = llm_profile_repo.get_by_id(int(aid))
        if prof:
            return _overlay_saved_row(params, prof)
    return _overlay_saved_row(params, row)


def profile_row_to_litellm_params(profile_row: Dict[str, Any]) -> Dict[str, Any]:
    """Merge env defaults with one profile row (health checks, fallback chain)."""
    return _overlay_saved_row(dict(settings.llm_params), profile_row)


def saved_settings_apply(row: Dict[str, Any] | None) -> bool:
    """Whether DB saved config should be treated as overriding env for UI effective_source."""
    if not row:
        return False
    if row.get("active_profile_id"):
        prof = llm_profile_repo.get_by_id(int(row["active_profile_id"]))
        if prof:
            return True
    return bool(
        (row.get("model") and str(row["model"]).strip())
        or (row.get("api_base") and str(row["api_base"]).strip())
        or row.get("api_key")
    )
