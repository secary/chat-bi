"""Runtime LLM configuration stored in MySQL (overrides env)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from backend.app_llm import effective_llm_params, saved_settings_apply
from backend import llm_profile_repo
from backend import llm_settings_repo
from backend.http_utils import request_trace_id
from backend.trace import log_event

router = APIRouter(prefix="/admin", tags=["admin"])


class LlmSettingsPut(BaseModel):
    model: Optional[str] = Field(default=None, max_length=255)
    api_base: Optional[str] = Field(default=None, max_length=512)
    api_key: Optional[str] = Field(default=None, max_length=512)


@router.get("/llm-settings")
def get_llm_settings(request: Request) -> dict:
    row = llm_settings_repo.get_row()
    view = llm_settings_repo.public_view(row)
    profiles = llm_profile_repo.list_ordered()
    view["profiles"] = [llm_profile_repo.public_row(p) for p in profiles]
    effective = effective_llm_params()
    view["effective_model"] = effective.get("model")
    view["effective_api_base"] = effective.get("api_base")
    view["effective_api_key_set"] = bool(effective.get("api_key"))
    view["effective_source"] = "saved_settings" if saved_settings_apply(row) else "env"
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
    view = llm_settings_repo.public_view(row)
    profiles = llm_profile_repo.list_ordered()
    view["profiles"] = [llm_profile_repo.public_row(p) for p in profiles]
    effective = effective_llm_params()
    view["effective_model"] = effective.get("model")
    view["effective_api_base"] = effective.get("api_base")
    view["effective_api_key_set"] = bool(effective.get("api_key"))
    view["effective_source"] = "saved_settings" if saved_settings_apply(row) else "env"
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
