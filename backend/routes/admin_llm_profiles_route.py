"""Admin CRUD for llm_model_profile + connectivity test."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from backend.app_llm import profile_row_to_litellm_params
from backend.http_utils import request_trace_id
from backend import llm_profile_repo
from backend.trace import log_event

router = APIRouter(prefix="/admin", tags=["admin"])


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
    pid = llm_profile_repo.create(body.display_name, m, body.api_base, body.api_key)
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
    if body.profile_id is not None:
        if not llm_profile_repo.get_by_id(body.profile_id):
            raise HTTPException(status_code=404, detail="档案不存在")
    llm_profile_repo.set_active_profile(body.profile_id)
    log_event(
        trace_id,
        "admin.llm_settings",
        "active_profile_set",
        payload={"profile_id": body.profile_id},
    )
    return {"ok": True}


async def _probe_profile(profile_id: int) -> tuple[bool, str]:
    from litellm import acompletion

    row = llm_profile_repo.get_by_id(profile_id)
    if not row:
        return False, "档案不存在"
    params = profile_row_to_litellm_params(row)
    try:
        await acompletion(
            **params,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1,
            temperature=0,
            timeout=25,
        )
        llm_profile_repo.set_health(profile_id, "ok", None)
        return True, "ok"
    except Exception as exc:
        msg = f"{type(exc).__name__}: {exc}"
        if len(msg) > 500:
            msg = msg[:500] + "…"
        llm_profile_repo.set_health(profile_id, "error", msg)
        return False, msg


@router.post("/llm-profiles/{profile_id:int}/test")
async def test_llm_profile(profile_id: int, request: Request) -> dict:
    trace_id = request_trace_id(request)
    ok, message = await _probe_profile(profile_id)
    log_event(
        trace_id,
        "admin.llm_settings",
        "profile_tested",
        payload={"profile_id": profile_id, "ok": ok},
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
