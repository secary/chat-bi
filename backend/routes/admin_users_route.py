"""Admin-only user CRUD."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from backend.auth_deps import require_admin
from backend.auth_password import hash_password
from backend.http_utils import request_trace_id
from backend.trace import log_event
from backend.user_repo import (
    create_user,
    get_by_id,
    get_by_username,
    list_users,
    update_user,
)

router = APIRouter(prefix="/admin/users", tags=["admin-users"])


class UserCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=120)
    password: str = Field(..., min_length=1, max_length=256)
    role: str = Field(default="user", max_length=32)


class UserPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    password: Optional[str] = Field(default=None, max_length=256)
    role: Optional[str] = Field(default=None, max_length=32)
    is_active: Optional[bool] = None


@router.get("")
def get_users(
    request: Request, admin: Dict[str, Any] = Depends(require_admin)
) -> List[dict]:
    log_event(
        request_trace_id(request),
        "admin.users",
        "listed",
        payload={"admin_user_id": int(admin["id"])},
    )
    return list_users()


@router.post("")
def post_user(
    body: UserCreate, request: Request, admin: Dict[str, Any] = Depends(require_admin)
) -> dict:
    trace_id = request_trace_id(request)
    if get_by_username(body.username.strip()):
        log_event(
            trace_id,
            "admin.users",
            "create_failed",
            "username exists",
            payload={"admin_user_id": int(admin["id"]), "username": body.username.strip()},
            level="WARN",
        )
        raise HTTPException(status_code=400, detail="用户名已存在")
    hid = hash_password(body.password)
    role = body.role.strip() if body.role.strip() in ("admin", "user") else "user"
    uid = create_user(body.username.strip(), hid, role)
    log_event(
        trace_id,
        "admin.users",
        "created",
        payload={
            "admin_user_id": int(admin["id"]),
            "target_user_id": uid,
            "username": body.username.strip(),
            "role": role,
        },
    )
    return {"id": uid}


@router.patch("/{user_id}")
def patch_user(
    user_id: int,
    body: UserPatch,
    request: Request,
    admin: Dict[str, Any] = Depends(require_admin),
) -> dict:
    trace_id = request_trace_id(request)
    payload = body.model_dump(exclude_unset=True)
    if user_id == admin["id"] and payload.get("is_active") is False:
        log_event(
            trace_id,
            "admin.users",
            "update_failed",
            "cannot deactivate current admin",
            payload={"admin_user_id": int(admin["id"]), "target_user_id": user_id},
            level="WARN",
        )
        raise HTTPException(status_code=400, detail="不能禁用当前登录管理员")
    if not get_by_id(user_id):
        log_event(
            trace_id,
            "admin.users",
            "update_failed",
            "user not found",
            payload={"admin_user_id": int(admin["id"]), "target_user_id": user_id},
            level="WARN",
        )
        raise HTTPException(status_code=404, detail="用户不存在")
    ph: Optional[str] = None
    if payload.get("password"):
        ph = hash_password(str(payload["password"]))
    role_val: Optional[str] = None
    if "role" in payload and payload["role"] is not None:
        r = str(payload["role"]).strip()
        if r not in ("admin", "user"):
            raise HTTPException(status_code=400, detail="非法角色")
        role_val = r
    update_user(
        user_id,
        password_hash=ph,
        role=role_val,
        is_active=payload.get("is_active") if "is_active" in payload else None,
    )
    log_event(
        trace_id,
        "admin.users",
        "updated",
        payload={
            "admin_user_id": int(admin["id"]),
            "target_user_id": user_id,
            "changed_fields": sorted(payload.keys()),
            "role": role_val,
            "is_active": payload.get("is_active") if "is_active" in payload else None,
            "password_changed": ph is not None,
        },
    )
    return {"ok": True}


@router.delete("/{user_id}")
def delete_user_route(
    user_id: int, request: Request, admin: Dict[str, Any] = Depends(require_admin)
) -> dict:
    trace_id = request_trace_id(request)
    if user_id == admin["id"]:
        log_event(
            trace_id,
            "admin.users",
            "deactivate_failed",
            "cannot deactivate current admin",
            payload={"admin_user_id": int(admin["id"]), "target_user_id": user_id},
            level="WARN",
        )
        raise HTTPException(status_code=400, detail="不能删除当前登录用户")
    if not get_by_id(user_id):
        log_event(
            trace_id,
            "admin.users",
            "deactivate_failed",
            "user not found",
            payload={"admin_user_id": int(admin["id"]), "target_user_id": user_id},
            level="WARN",
        )
        raise HTTPException(status_code=404, detail="用户不存在")
    update_user(user_id, is_active=False)
    log_event(
        trace_id,
        "admin.users",
        "deactivated",
        payload={"admin_user_id": int(admin["id"]), "target_user_id": user_id},
    )
    return {"ok": True}
