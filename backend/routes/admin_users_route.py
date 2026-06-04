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
ROOT_USERNAME = "root"
ROOT_ROLE = "root"
ADMIN_ROLE = "admin"
USER_ROLE = "user"


class UserCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=120)
    password: str = Field(..., min_length=1, max_length=256)
    role: str = Field(default="user", max_length=32)


class UserPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    password: Optional[str] = Field(default=None, max_length=256)
    role: Optional[str] = Field(default=None, max_length=32)
    is_active: Optional[bool] = None


def _is_root_user(row: Dict[str, Any] | None) -> bool:
    return bool(
        row and (str(row.get("username")) == ROOT_USERNAME or str(row.get("role")) == ROOT_ROLE)
    )


def _is_admin_user(row: Dict[str, Any] | None) -> bool:
    return bool(row and str(row.get("role")) == ADMIN_ROLE)


def _current_admin_is_root(admin: Dict[str, Any]) -> bool:
    return str(admin.get("username")) == ROOT_USERNAME or str(admin.get("role")) == ROOT_ROLE


def _validate_role(value: str) -> str:
    role = value.strip()
    if role not in (ROOT_ROLE, ADMIN_ROLE, USER_ROLE):
        raise HTTPException(status_code=400, detail="非法角色")
    return role


@router.get("")
def get_users(request: Request, admin: Dict[str, Any] = Depends(require_admin)) -> List[dict]:
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
    username = body.username.strip()
    if username == ROOT_USERNAME:
        log_event(
            trace_id,
            "admin.users",
            "create_failed",
            "root username is reserved",
            payload={"admin_user_id": int(admin["id"]), "username": username},
            level="WARN",
        )
        raise HTTPException(status_code=400, detail="root 是系统内置超级管理员")
    if get_by_username(username):
        log_event(
            trace_id,
            "admin.users",
            "create_failed",
            "username exists",
            payload={"admin_user_id": int(admin["id"]), "username": username},
            level="WARN",
        )
        raise HTTPException(status_code=400, detail="用户名已存在")
    hid = hash_password(body.password)
    role = _validate_role(body.role)
    if role == ROOT_ROLE:
        log_event(
            trace_id,
            "admin.users",
            "create_failed",
            "root role is reserved",
            payload={"admin_user_id": int(admin["id"]), "username": username},
            level="WARN",
        )
        raise HTTPException(status_code=400, detail="root 账号是系统唯一内置账号")
    if role == ADMIN_ROLE and not _current_admin_is_root(admin):
        log_event(
            trace_id,
            "admin.users",
            "create_failed",
            "only root can create administrators",
            payload={"admin_user_id": int(admin["id"]), "username": username},
            level="WARN",
        )
        raise HTTPException(status_code=403, detail="只有 root 可以创建管理员")
    uid = create_user(username, hid, role)
    log_event(
        trace_id,
        "admin.users",
        "created",
        payload={
            "admin_user_id": int(admin["id"]),
            "target_user_id": uid,
            "username": username,
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
    target = get_by_id(user_id)
    if not target:
        log_event(
            trace_id,
            "admin.users",
            "update_failed",
            "user not found",
            payload={"admin_user_id": int(admin["id"]), "target_user_id": user_id},
            level="WARN",
        )
        raise HTTPException(status_code=404, detail="用户不存在")
    current_is_root = _current_admin_is_root(admin)
    target_is_root = _is_root_user(target)
    target_is_admin = _is_admin_user(target)

    if target_is_root:
        if not current_is_root:
            log_event(
                trace_id,
                "admin.users",
                "update_failed",
                "only root can update root",
                payload={"admin_user_id": int(admin["id"]), "target_user_id": user_id},
                level="WARN",
            )
            raise HTTPException(status_code=403, detail="只有 root 可以管理 root 账号")
        if "role" in payload or "is_active" in payload:
            log_event(
                trace_id,
                "admin.users",
                "update_failed",
                "root role and status are immutable",
                payload={"admin_user_id": int(admin["id"]), "target_user_id": user_id},
                level="WARN",
            )
            raise HTTPException(status_code=400, detail="root 不能降级或停用")

    if target_is_admin and not current_is_root:
        changed_fields = set(payload.keys())
        if user_id != admin["id"] or changed_fields - {"password"}:
            log_event(
                trace_id,
                "admin.users",
                "update_failed",
                "only root can manage administrators",
                payload={"admin_user_id": int(admin["id"]), "target_user_id": user_id},
                level="WARN",
            )
            raise HTTPException(status_code=403, detail="只有 root 可以管理管理员")

    ph: Optional[str] = None
    if payload.get("password"):
        ph = hash_password(str(payload["password"]))
    role_val: Optional[str] = None
    if "role" in payload and payload["role"] is not None:
        role_val = _validate_role(str(payload["role"]))
        if role_val == ROOT_ROLE:
            raise HTTPException(status_code=400, detail="root 账号是系统唯一内置账号")
        if role_val == ADMIN_ROLE and not current_is_root:
            raise HTTPException(status_code=403, detail="只有 root 可以授予管理员角色")
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
    target = get_by_id(user_id)
    if not target:
        log_event(
            trace_id,
            "admin.users",
            "deactivate_failed",
            "user not found",
            payload={"admin_user_id": int(admin["id"]), "target_user_id": user_id},
            level="WARN",
        )
        raise HTTPException(status_code=404, detail="用户不存在")
    if _is_root_user(target):
        log_event(
            trace_id,
            "admin.users",
            "deactivate_failed",
            "root is immutable",
            payload={"admin_user_id": int(admin["id"]), "target_user_id": user_id},
            level="WARN",
        )
        raise HTTPException(status_code=400, detail="root 不能删除或停用")
    if _is_admin_user(target) and not _current_admin_is_root(admin):
        log_event(
            trace_id,
            "admin.users",
            "deactivate_failed",
            "only root can deactivate administrators",
            payload={"admin_user_id": int(admin["id"]), "target_user_id": user_id},
            level="WARN",
        )
        raise HTTPException(status_code=403, detail="只有 root 可以停用管理员")
    update_user(user_id, is_active=False)
    log_event(
        trace_id,
        "admin.users",
        "deactivated",
        payload={"admin_user_id": int(admin["id"]), "target_user_id": user_id},
    )
    return {"ok": True}
