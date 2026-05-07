"""Admin-only user CRUD."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from backend.auth_deps import require_admin
from backend.auth_password import hash_password
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
def get_users(_admin: Dict[str, Any] = Depends(require_admin)) -> List[dict]:
    return list_users()


@router.post("")
def post_user(
    body: UserCreate, admin: Dict[str, Any] = Depends(require_admin)
) -> dict:
    if get_by_username(body.username.strip()):
        raise HTTPException(status_code=400, detail="用户名已存在")
    hid = hash_password(body.password)
    role = body.role.strip() if body.role.strip() in ("admin", "user") else "user"
    uid = create_user(body.username.strip(), hid, role)
    return {"id": uid}


@router.patch("/{user_id}")
def patch_user(
    user_id: int,
    body: UserPatch,
    admin: Dict[str, Any] = Depends(require_admin),
) -> dict:
    payload = body.model_dump(exclude_unset=True)
    if user_id == admin["id"] and payload.get("is_active") is False:
        raise HTTPException(status_code=400, detail="不能禁用当前登录管理员")
    if not get_by_id(user_id):
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
    return {"ok": True}


@router.delete("/{user_id}")
def delete_user_route(
    user_id: int, admin: Dict[str, Any] = Depends(require_admin)
) -> dict:
    if user_id == admin["id"]:
        raise HTTPException(status_code=400, detail="不能删除当前登录用户")
    if not get_by_id(user_id):
        raise HTTPException(status_code=404, detail="用户不存在")
    update_user(user_id, is_active=False)
    return {"ok": True}
