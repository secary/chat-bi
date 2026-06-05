"""Admin CRUD for llm_model_profile + connectivity test."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from backend.app_llm import profile_row_to_litellm_params
from backend.config import settings
from backend.http_utils import request_trace_id
from backend import llm_profile_repo
from backend import llm_settings_repo
from backend.trace import log_event

router = APIRouter(prefix="/admin", tags=["admin"])
ENV_DEFAULT_PROFILE_ID = 0


class LlmProfileCreate(BaseModel):
    display_name: Optional[str] = Field(default=None, max_length=128)
    model: str = Field(..., max_length=255)
    api_base: Optional[str] = Field(default=None, max_length=512)
    api_key: Optional[str] = Field(default=None, max_length=512)


class LlmProfileUpdate(BaseModel):
    display_name: Optional[str] = Field(default=None, max_length=128)
    model: Optional[str] = Field(default=None, max_length=255)
    api_base: Optional[str] = Field(default=None, max_length=512)
    api_key: Optional[str] = Field(default=None, max_length=512)


class LlmProfileProbe(BaseModel):
    model: str = Field(..., max_length=255)
    api_base: Optional[str] = Field(default=None, max_length=512)
    api_key: Optional[str] = Field(default=None, max_length=512)
    source_profile_id: Optional[int] = None


class ReorderBody(BaseModel):
    ordered_ids: List[int] = Field(..., min_length=1)


class ActiveBody(BaseModel):
    profile_id: Optional[int] = None


@router.post("/llm-profiles")
def create_llm_profile(body: LlmProfileCreate, request: Request) -> dict:
    trace_id = request_trace_id(request)
    m = body.model.strip()
    if not m:
        raise HTTPException(status_code=400, detail="模型名不能为空")
    pid = llm_profile_repo.create(
        body.display_name,
        m,
        body.api_base,
        body.api_key,
    )
    rows = llm_profile_repo.list_ordered()
    if len(rows) == 1:
        llm_profile_repo.set_active_profile(pid)
    row = llm_profile_repo.get_by_id(pid)
    log_event(
        trace_id,
        "admin.llm_settings",
        "profile_created",
        payload={"profile_id": pid},
    )
    return {"profile": llm_profile_repo.public_row(row)} if row else {"profile": None}


@router.put("/llm-profiles/{profile_id:int}")
def update_llm_profile(profile_id: int, body: LlmProfileUpdate, request: Request) -> dict:
    trace_id = request_trace_id(request)
    if not llm_profile_repo.get_by_id(profile_id):
        raise HTTPException(status_code=404, detail="档案不存在")
    data = body.model_dump(exclude_unset=True)
    if "model" in data:
        mv = (data.get("model") or "").strip()
        if not mv:
            raise HTTPException(status_code=400, detail="模型名不能为空")
        data["model"] = mv
    llm_profile_repo.update(
        profile_id,
        display_name=data.get("display_name"),
        model=data.get("model"),
        api_base=data.get("api_base"),
        api_key=data.get("api_key"),
    )
    row = llm_profile_repo.get_by_id(profile_id)
    log_event(
        trace_id,
        "admin.llm_settings",
        "profile_updated",
        payload={"profile_id": profile_id, "fields": sorted(data.keys())},
    )
    return {"profile": llm_profile_repo.public_row(row)} if row else {"profile": None}


@router.delete("/llm-profiles/{profile_id:int}")
def delete_llm_profile(profile_id: int, request: Request) -> dict:
    trace_id = request_trace_id(request)
    if not llm_profile_repo.get_by_id(profile_id):
        raise HTTPException(status_code=404, detail="档案不存在")
    llm_profile_repo.delete_profile(profile_id)
    log_event(
        trace_id,
        "admin.llm_settings",
        "profile_deleted",
        payload={"profile_id": profile_id},
    )
    return {"ok": True}


@router.put("/llm-profiles/reorder")
def reorder_llm_profiles(body: ReorderBody, request: Request) -> dict:
    trace_id = request_trace_id(request)
    existing = llm_profile_repo.list_ordered()
    ids_db = {int(r["id"]) for r in existing}
    ids_req = list(body.ordered_ids)
    if set(ids_req) != ids_db or len(ids_req) != len(ids_db):
        raise HTTPException(status_code=400, detail="ordered_ids 必须与当前全部档案 id 一致")
    llm_profile_repo.reorder(ids_req)
    log_event(trace_id, "admin.llm_settings", "profiles_reordered", payload={"order": ids_req})
    return {"ok": True}


@router.put("/llm-profiles/active")
def set_active_llm_profile(body: ActiveBody, request: Request) -> dict:
    trace_id = request_trace_id(request)
    if body.profile_id in (None, ENV_DEFAULT_PROFILE_ID):
        llm_settings_repo.activate_env_defaults()
        profile_id = ENV_DEFAULT_PROFILE_ID
    else:
        if not llm_profile_repo.get_by_id(body.profile_id):
            raise HTTPException(status_code=404, detail="档案不存在")
        llm_profile_repo.set_active_profile(body.profile_id)
        profile_id = body.profile_id
    log_event(
        trace_id,
        "admin.llm_settings",
        "active_profile_set",
        payload={"profile_id": profile_id},
    )
    return {"ok": True}


def _test_log_payload(**payload: object) -> dict:
    message = str(payload.get("message") or "")
    ok = payload.get("ok")
    if ok is not False or not message:
        payload.pop("message", None)
    return dict(payload)


async def _probe_litellm_params(params: dict) -> tuple[bool, str]:
    from litellm import acompletion

    try:
        await acompletion(
            **params,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1,
            temperature=0,
            timeout=25,
        )
        return True, "ok"
    except Exception as exc:
        return False, _friendly_probe_error(exc)


def _friendly_probe_error(exc: Exception) -> str:
    raw = str(exc)
    lower = f"{type(exc).__name__}: {raw}".lower()
    if any(
        token in lower for token in ("authentication", "unauthorized", "invalid api key", "401")
    ):
        return "请填写正确的 API Key。"
    if any(token in lower for token in ("model_not_found", "not found", "unknown model", "404")):
        return "请填写正确的模型名。"
    if any(token in lower for token in ("timeout", "timed out")):
        return "请填写正确的 Base URL。"
    if any(
        token in lower
        for token in (
            "connection",
            "connecterror",
            "name resolution",
            "dns",
            "no address associated",
            "connection refused",
        )
    ):
        return "请填写正确的 Base URL。"
    if any(token in lower for token in ("rate limit", "ratelimit", "quota", "insufficient", "429")):
        return "请填写正确的 API Key。"
    if any(token in lower for token in ("badrequest", "bad request", "invalid request", "400")):
        return "请填写正确的模型名、Base URL 和 API Key。"
    detail = raw.strip()
    if len(detail) > 180:
        detail = detail[:180] + "…"
    if detail:
        return f"连接测试失败：{detail}"
    return "请填写正确的模型名、Base URL 和 API Key。"


async def _probe_profile(profile_id: int) -> tuple[bool, str]:
    if profile_id == ENV_DEFAULT_PROFILE_ID:
        return await _probe_litellm_params(dict(settings.llm_params))
    row = llm_profile_repo.get_by_id(profile_id)
    if not row:
        return False, "档案不存在"
    params = profile_row_to_litellm_params(row)
    ok, message = await _probe_litellm_params(params)
    llm_profile_repo.set_health(profile_id, "ok" if ok else "error", None if ok else message)
    return ok, message


@router.post("/llm-profiles/probe")
async def probe_llm_profile(body: LlmProfileProbe, request: Request) -> dict:
    trace_id = request_trace_id(request)
    model = body.model.strip()
    if not model:
        raise HTTPException(status_code=400, detail="模型名不能为空")
    api_key = body.api_key
    if not api_key and body.source_profile_id is not None:
        row = llm_profile_repo.get_by_id(body.source_profile_id)
        if not row:
            raise HTTPException(status_code=404, detail="档案不存在")
        api_key = row.get("api_key")
    params = profile_row_to_litellm_params(
        {
            "model": model,
            "api_base": body.api_base,
            "api_key": api_key,
        }
    )
    ok, message = await _probe_litellm_params(params)
    log_event(
        trace_id,
        "admin.llm_settings",
        "profile_probe_tested",
        payload=_test_log_payload(model=model, ok=ok, message=message),
    )
    return {"ok": ok, "message": message}


@router.post("/llm-profiles/{profile_id:int}/test")
async def test_llm_profile(profile_id: int, request: Request) -> dict:
    trace_id = request_trace_id(request)
    ok, message = await _probe_profile(profile_id)
    log_event(
        trace_id,
        "admin.llm_settings",
        "profile_tested",
        payload=_test_log_payload(profile_id=profile_id, ok=ok, message=message),
    )
    return {"ok": ok, "message": message}


@router.post("/llm-profiles/test-all")
async def test_all_llm_profiles(request: Request) -> dict:
    trace_id = request_trace_id(request)
    rows = llm_profile_repo.list_ordered()
    results: List[dict] = []
    for r in rows:
        pid = int(r["id"])
        ok, message = await _probe_profile(pid)
        results.append({"id": pid, "ok": ok, "message": message})
    log_event(
        trace_id,
        "admin.llm_settings",
        "profiles_test_all",
        payload={"count": len(results)},
    )
    return {"results": results}
