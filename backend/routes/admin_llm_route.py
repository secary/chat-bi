"""Runtime LLM configuration stored in MySQL (overrides env)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from backend.app_llm import effective_llm_params, saved_settings_apply
from backend import llm_profile_repo
from backend import llm_settings_repo
from backend.config import settings
from backend.http_utils import request_trace_id
from backend.trace import log_event

router = APIRouter(prefix="/admin", tags=["admin"])
ENV_DEFAULT_PROFILE_ID = 0


class LlmSettingsPut(BaseModel):
    model: Optional[str] = Field(default=None, max_length=255)
    api_base: Optional[str] = Field(default=None, max_length=512)
    api_key: Optional[str] = Field(default=None, max_length=512)


def _env_default_profile() -> dict:
    env = settings.llm_params
    return {
        "id": ENV_DEFAULT_PROFILE_ID,
        "display_name": "默认配置",
        "model": env.get("model"),
        "api_base": env.get("api_base"),
        "api_key_set": bool(env.get("api_key")),
        "sort_order": -1,
        "health_status": "unknown",
        "health_detail": None,
        "health_checked_at": None,
        "created_at": None,
        "updated_at": None,
        "is_env_default": True,
    }


def _settings_view(row: dict | None) -> dict:
    view = llm_settings_repo.public_view(row)
    profiles = [_env_default_profile()]
    profiles.extend(llm_profile_repo.public_row(p) for p in llm_profile_repo.list_ordered())
    view["profiles"] = profiles
    effective = effective_llm_params()
    view["effective_model"] = effective.get("model")
    view["effective_api_base"] = effective.get("api_base")
    view["effective_api_key_set"] = bool(effective.get("api_key"))
    view["effective_source"] = "saved_settings" if saved_settings_apply(row) else "env"
    return view


@router.get("/llm-settings")
def get_llm_settings(request: Request) -> dict:
    row = llm_settings_repo.get_row()
    view = _settings_view(row)
    log_event(
        request_trace_id(request),
        "admin.llm_settings",
        "viewed",
        payload={
            "effective_model": view.get("effective_model"),
            "effective_source": view.get("effective_source"),
            "saved_model": view.get("model"),
            "profile_count": len(view.get("profiles") or []),
            "active_profile_id": view.get("active_profile_id"),
        },
    )
    return view


@router.put("/llm-settings")
def put_llm_settings(body: LlmSettingsPut, request: Request) -> dict:
    trace_id = request_trace_id(request)
    data = body.model_dump(exclude_unset=True)
    llm_settings_repo.save_merged(
        model=data.get("model"),
        api_base=data.get("api_base"),
        api_key=data.get("api_key"),
    )
    row = llm_settings_repo.get_row()
    view = _settings_view(row)
    log_event(
        trace_id,
        "admin.llm_settings",
        "updated",
        payload={
            "changed_fields": sorted(data.keys()),
            "effective_model": view.get("effective_model"),
            "effective_source": view.get("effective_source"),
            "api_key_updated": "api_key" in data,
        },
    )
    return view
