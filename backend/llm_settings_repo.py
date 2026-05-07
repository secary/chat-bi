"""Row id=1 llm_settings for UI-driven model configuration."""

from __future__ import annotations

from typing import Any, Dict, Optional

from backend.db_mysql import admin_execute, admin_fetch_one


def get_row() -> Optional[Dict[str, Any]]:
    try:
        return admin_fetch_one(
            "SELECT id, model, api_base, api_key, updated_at FROM llm_settings WHERE id = 1"
        )
    except Exception:
        return None


def save_merged(
    model: Optional[str] = None,
    api_base: Optional[str] = None,
    api_key: Optional[str] = None,
) -> None:
    """Missing arguments keep existing DB values. Empty string clears a column."""
    row = get_row()
    m = _pick(model, (row or {}).get("model"))
    b = _pick(api_base, (row or {}).get("api_base"))
    k = _pick(api_key, (row or {}).get("api_key"))
    admin_execute(
        "REPLACE INTO llm_settings (id, model, api_base, api_key) VALUES (1, %s, %s, %s)",
        (_blank_to_none(m), _blank_to_none(b), _blank_to_none(k)),
    )


def _pick(new_val: Optional[str], old_val: Any) -> Any:
    if new_val is None:
        return old_val
    return new_val


def _blank_to_none(val: Any) -> Any:
    if val == "":
        return None
    return val


def public_view(row: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not row:
        return {
            "model": None,
            "api_base": None,
            "api_key_set": False,
            "updated_at": None,
        }
    has_key = bool(row.get("api_key"))
    return {
        "model": row.get("model"),
        "api_base": row.get("api_base"),
        "api_key_set": has_key,
        "updated_at": row.get("updated_at"),
    }
