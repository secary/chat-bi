"""CRUD for llm_model_profile (admin DB)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.db_mysql import (
    admin_execute,
    admin_execute_lastrowid,
    admin_fetch_all,
    admin_fetch_one,
)


def _blank_to_none(val: Any) -> Any:
    if val == "":
        return None
    return val


def list_ordered() -> List[Dict[str, Any]]:
    try:
        return admin_fetch_all(
            "SELECT id, display_name, model, api_base, api_key, sort_order, "
            "health_status, health_detail, health_checked_at, created_at, updated_at "
            "FROM llm_model_profile ORDER BY sort_order ASC, id ASC"
        )
    except Exception:
        return []


def get_by_id(profile_id: int) -> Optional[Dict[str, Any]]:
    try:
        return admin_fetch_one(
            "SELECT id, display_name, model, api_base, api_key, sort_order, "
            "health_status, health_detail, health_checked_at, created_at, updated_at "
            "FROM llm_model_profile WHERE id = %s",
            (profile_id,),
        )
    except Exception:
        return None


def public_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "display_name": row.get("display_name"),
        "model": row.get("model"),
        "api_base": row.get("api_base"),
        "api_key_set": bool(row.get("api_key")),
        "sort_order": row.get("sort_order", 0),
        "health_status": row.get("health_status") or "unknown",
        "health_detail": row.get("health_detail"),
        "health_checked_at": row.get("health_checked_at"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


def _next_sort_order() -> int:
    r = admin_fetch_one("SELECT COALESCE(MAX(sort_order), -1) AS m FROM llm_model_profile")
    if not r:
        return 0
    return int(r["m"]) + 1


def create(
    display_name: Optional[str],
    model: str,
    api_base: Optional[str],
    api_key: Optional[str],
) -> int:
    sort_order = _next_sort_order()
    # Must use same DB session as INSERT — LAST_INSERT_ID() is per-connection.
    return admin_execute_lastrowid(
        "INSERT INTO llm_model_profile "
        "(display_name, model, api_base, api_key, sort_order, health_status) "
        "VALUES (%s, %s, %s, %s, %s, 'unknown')",
        (
            display_name,
            model.strip(),
            _blank_to_none(api_base),
            _blank_to_none(api_key),
            sort_order,
        ),
    )


def update(
    profile_id: int,
    display_name: Optional[str] = None,
    model: Optional[str] = None,
    api_base: Optional[str] = None,
    api_key: Optional[str] = None,
) -> None:
    row = get_by_id(profile_id)
    if not row:
        return
    dn = display_name if display_name is not None else row.get("display_name")
    m = model.strip() if model is not None else row.get("model")
    b = _blank_to_none(api_base) if api_base is not None else row.get("api_base")
    if api_key is None:
        k = row.get("api_key")
    elif api_key == "":
        k = row.get("api_key")
    else:
        k = _blank_to_none(api_key)
    admin_execute(
        "UPDATE llm_model_profile SET display_name = %s, model = %s, api_base = %s, api_key = %s "
        "WHERE id = %s",
        (dn, m, b, k, profile_id),
    )


def set_health(profile_id: int, status: str, detail: Optional[str]) -> None:
    admin_execute(
        "UPDATE llm_model_profile SET health_status = %s, health_detail = %s, "
        "health_checked_at = CURRENT_TIMESTAMP(6) WHERE id = %s",
        (status, detail, profile_id),
    )


def reorder(ordered_ids: List[int]) -> None:
    for i, pid in enumerate(ordered_ids):
        admin_execute(
            "UPDATE llm_model_profile SET sort_order = %s WHERE id = %s",
            (i, pid),
        )


def set_active_profile(profile_id: Optional[int]) -> None:
    admin_execute(
        "UPDATE llm_settings SET active_profile_id = %s WHERE id = 1",
        (profile_id,),
    )


def delete_profile(profile_id: int) -> None:
    from backend import llm_settings_repo

    settings_row = llm_settings_repo.get_row()
    active = settings_row.get("active_profile_id") if settings_row else None
    admin_execute("DELETE FROM llm_model_profile WHERE id = %s", (profile_id,))
    if active == profile_id:
        nxt = admin_fetch_one(
            "SELECT id FROM llm_model_profile ORDER BY sort_order ASC, id ASC LIMIT 1"
        )
        new_active: Optional[int] = int(nxt["id"]) if nxt and nxt.get("id") is not None else None
        set_active_profile(new_active)
