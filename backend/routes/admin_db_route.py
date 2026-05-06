"""MySQL connection registry for Skill subprocess env injection."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.connection_repo import (
    delete_connection,
    get_connection,
    insert_connection,
    list_connections,
    update_connection,
)
from backend.db_mysql import test_mysql_connection

router = APIRouter(prefix="/admin", tags=["admin"])


class DbConnectionCreate(BaseModel):
    name: str = Field(..., max_length=120)
    host: str = Field(..., max_length=255)
    port: int = Field(default=3306, ge=1, le=65535)
    username: str = Field(..., max_length=120)
    password: str = Field(default="", max_length=512)
    database_name: str = Field(..., max_length=120)
    is_default: bool = False


class DbConnectionUpdate(BaseModel):
    name: str = Field(..., max_length=120)
    host: str = Field(..., max_length=255)
    port: int = Field(default=3306, ge=1, le=65535)
    username: str = Field(..., max_length=120)
    password: Optional[str] = Field(default=None, max_length=512)
    database_name: str = Field(..., max_length=120)
    is_default: bool = False


@router.get("/db-connections")
def list_db_connections() -> List[dict]:
    return list_connections()


@router.post("/db-connections")
def create_db_connection(body: DbConnectionCreate) -> dict:
    cid = insert_connection(
        body.name,
        body.host,
        body.port,
        body.username,
        body.password,
        body.database_name,
        body.is_default,
    )
    row = get_connection(cid)
    if not row:
        raise HTTPException(status_code=500, detail="创建失败")
    out = dict(row)
    out.pop("password", None)
    return out


@router.put("/db-connections/{conn_id:int}")
def put_db_connection(conn_id: int, body: DbConnectionUpdate) -> dict:
    if not get_connection(conn_id):
        raise HTTPException(status_code=404, detail="连接不存在")
    update_connection(
        conn_id,
        body.name,
        body.host,
        body.port,
        body.username,
        body.password,
        body.database_name,
        body.is_default,
    )
    row = get_connection(conn_id)
    if row:
        row.pop("password", None)
    return row or {}


@router.delete("/db-connections/{conn_id:int}")
def remove_db_connection(conn_id: int) -> dict:
    if not get_connection(conn_id):
        raise HTTPException(status_code=404, detail="连接不存在")
    delete_connection(conn_id)
    return {"ok": True}


@router.post("/db-connections/{conn_id:int}/test")
def test_db_connection(conn_id: int) -> dict:
    row = get_connection(conn_id)
    if not row:
        raise HTTPException(status_code=404, detail="连接不存在")
    try:
        test_mysql_connection(
            str(row["host"]),
            int(row["port"]),
            str(row["username"]),
            str(row["password"]),
            str(row["database_name"]),
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True}
