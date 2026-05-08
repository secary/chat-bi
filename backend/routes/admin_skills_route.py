"""Skill filesystem CRUD + skill_registry enable/disable."""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from backend.agent.prompt_builder import scan_skills
from backend.config import settings
from backend.http_utils import request_trace_id
from backend.skill_registry_repo import disabled_slugs, set_enabled
from backend.trace import log_event

router = APIRouter(prefix="/admin", tags=["admin"])

_SAFE_SLUG = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,126}$")


def _ensure_under_skills_root(target: Path) -> Path:
    if not _SAFE_SLUG.match(target.name):
        raise HTTPException(status_code=400, detail="非法 skill slug")
    root = settings.skills_dir.resolve()
    resolved = target.resolve()
    if resolved != root and root not in resolved.parents:
        raise HTTPException(status_code=400, detail="路径非法")
    return target


def _skill_path(slug: str) -> Path:
    return _ensure_under_skills_root(settings.skills_dir / slug)


class SkillCreate(BaseModel):
    slug: str = Field(..., max_length=128)
    markdown: str = Field(default="", max_length=500_000)


class SkillPut(BaseModel):
    markdown: str = Field(..., max_length=500_000)


class SkillPatch(BaseModel):
    enabled: bool = True


def _default_skill_md(slug: str, body: str) -> str:
    text = body.strip()
    if text:
        return text
    return (
        f'---\nname: "{slug}"\ndescription: "新建 Skill"\n---\n\n'
        "## Workflow\n\n在此编写工作流与命令说明。\n\n"
        "## Safety\n\n演示环境只读查询。\n"
    )


@router.get("/skills")
def admin_list_skills(request: Request) -> List[dict]:
    blocked = disabled_slugs()
    docs = scan_skills(settings.skills_dir)
    rows = []
    for doc in docs:
        slug = doc.skill_dir.name
        rows.append(
            {
                "slug": slug,
                "name": doc.name,
                "description": doc.description,
                "enabled": slug not in blocked,
            }
        )
    log_event(
        request_trace_id(request),
        "admin.skills",
        "listed",
        payload={"count": len(rows), "disabled_count": len(blocked)},
    )
    return rows


@router.post("/skills")
def admin_create_skill(body: SkillCreate, request: Request) -> dict:
    trace_id = request_trace_id(request)
    slug = body.slug.strip()
    base = _skill_path(slug)
    if base.exists():
        log_event(
            trace_id,
            "admin.skills",
            "create_failed",
            "skill directory exists",
            payload={"slug": slug},
            level="WARN",
        )
        raise HTTPException(status_code=409, detail="技能目录已存在")
    base.mkdir(parents=True)
    (base / "SKILL.md").write_text(_default_skill_md(slug, body.markdown), encoding="utf-8")
    scripts = base / "scripts"
    scripts.mkdir(exist_ok=True)
    log_event(
        trace_id,
        "admin.skills",
        "created",
        payload={"slug": slug, "path": str(base)},
    )
    return {"slug": slug, "path": str(base)}


@router.put("/skills/{slug}")
def admin_put_skill(slug: str, body: SkillPut, request: Request) -> dict:
    trace_id = request_trace_id(request)
    skill_md = _skill_path(slug) / "SKILL.md"
    if not skill_md.is_file():
        log_event(
            trace_id,
            "admin.skills",
            "update_failed",
            "skill file not found",
            payload={"slug": slug},
            level="WARN",
        )
        raise HTTPException(status_code=404, detail="SKILL.md 不存在")
    skill_md.write_text(body.markdown, encoding="utf-8")
    log_event(
        trace_id,
        "admin.skills",
        "updated",
        payload={"slug": slug, "markdown_length": len(body.markdown)},
    )
    return {"ok": True}


@router.patch("/skills/{slug}")
def admin_patch_skill(slug: str, body: SkillPatch, request: Request) -> dict:
    _skill_path(slug)  # validate slug path
    set_enabled(slug, body.enabled)
    log_event(
        request_trace_id(request),
        "admin.skills",
        "toggled",
        payload={"slug": slug, "enabled": body.enabled},
    )
    return {"ok": True}


@router.delete("/skills/{slug}")
def admin_delete_skill(slug: str, request: Request) -> dict:
    trace_id = request_trace_id(request)
    base = _skill_path(slug)
    if not base.is_dir():
        log_event(
            trace_id,
            "admin.skills",
            "delete_failed",
            "skill not found",
            payload={"slug": slug},
            level="WARN",
        )
        raise HTTPException(status_code=404, detail="技能不存在")
    shutil.rmtree(base)
    log_event(
        trace_id,
        "admin.skills",
        "deleted",
        payload={"slug": slug, "path": str(base)},
    )
    return {"ok": True}


@router.get("/skills/{slug}/file")
def admin_get_skill_file(slug: str, request: Request) -> dict:
    trace_id = request_trace_id(request)
    skill_md = _skill_path(slug) / "SKILL.md"
    if not skill_md.is_file():
        log_event(
            trace_id,
            "admin.skills",
            "file_view_failed",
            "skill file not found",
            payload={"slug": slug},
            level="WARN",
        )
        raise HTTPException(status_code=404, detail="SKILL.md 不存在")
    content = skill_md.read_text(encoding="utf-8")
    log_event(
        trace_id,
        "admin.skills",
        "file_viewed",
        payload={"slug": slug, "markdown_length": len(content)},
    )
    return {"markdown": content}
