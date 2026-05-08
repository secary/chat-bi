from __future__ import annotations

import re
import uuid
from pathlib import Path
from time import perf_counter

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.env_loader import load_project_env
from backend.auth_deps import get_current_user, require_admin
from backend.http_utils import request_trace_id
from backend.routes.admin_db_route import router as admin_db_router
from backend.routes.admin_llm_route import router as admin_llm_router
from backend.routes.admin_multi_agents_route import router as admin_multi_agents_router
from backend.routes.admin_skills_route import router as admin_skills_router
from backend.routes.admin_users_route import router as admin_users_router
from backend.routes.auth_route import router as auth_router
from backend.routes.chat_route import router as chat_router
from backend.routes.dashboard_route import router as dashboard_router
from backend.routes.sessions_route import router as sessions_router
from backend.trace import log_event

load_project_env(Path(__file__).resolve().parent.parent)

app = FastAPI(title="ChatBI API", version="0.1.0")
UPLOAD_DIR = Path("/tmp/chatbi-uploads")
ALLOWED_UPLOAD_SUFFIXES = {
    ".csv",
    ".xlsx",
    ".xlsm",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(
    dashboard_router,
    dependencies=[Depends(get_current_user)],
)
app.include_router(sessions_router)
app.include_router(admin_llm_router, dependencies=[Depends(require_admin)])
app.include_router(admin_db_router, dependencies=[Depends(require_admin)])
app.include_router(admin_skills_router, dependencies=[Depends(require_admin)])
app.include_router(admin_multi_agents_router, dependencies=[Depends(require_admin)])
app.include_router(admin_users_router)


class UploadResult(BaseModel):
    filename: str
    server_path: str
    size: int
    trace_id: str


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/upload")
async def upload(
    request: Request,
    file: UploadFile = File(...),
    _user: dict = Depends(get_current_user),
):
    trace_id = request_trace_id(request)
    started_at = perf_counter()
    original_name = file.filename or "upload"
    log_event(
        trace_id,
        "http.upload",
        "request.started",
        payload={"filename": original_name, "content_type": file.content_type},
    )
    suffix = Path(original_name).suffix.lower()
    if suffix not in ALLOWED_UPLOAD_SUFFIXES:
        log_event(
            trace_id,
            "http.upload",
            "request.rejected",
            "unsupported suffix",
            {"suffix": suffix},
            "WARN",
        )
        raise HTTPException(
            status_code=400,
            detail="不支持的文件类型（允许 CSV、Excel 或 PNG/JPG/WebP 图像）",
        )

    safe_stem = re.sub(r"[^0-9A-Za-z._-]+", "_", Path(original_name).stem).strip("._")
    if not safe_stem:
        safe_stem = "upload"
    target = UPLOAD_DIR / f"{uuid.uuid4().hex}_{safe_stem}{suffix}"
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    size = 0
    with target.open("wb") as handle:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            handle.write(chunk)
    await file.close()

    if size == 0:
        target.unlink(missing_ok=True)
        log_event(trace_id, "http.upload", "request.rejected", "empty file", level="WARN")
        raise HTTPException(status_code=400, detail="上传文件为空")

    log_event(
        trace_id,
        "http.upload",
        "request.completed",
        payload={
            "server_path": str(target),
            "size": size,
            "elapsed_ms": round((perf_counter() - started_at) * 1000, 2),
        },
    )
    return UploadResult(
        filename=original_name,
        server_path=str(target),
        size=size,
        trace_id=trace_id,
    )
