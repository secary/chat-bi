"""Admin read/write for skills/_agents/registry.yaml (multi-agent lines)."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Set

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from backend.agent.multi_agent_registry import (
    load_registry_dict,
    max_agents_per_round as clamp_max_agents,
    write_registry_dict,
)
from backend.agent.prompt_builder import scan_skills
from backend.config import settings
from backend.http_utils import request_trace_id
from backend.trace import log_event

router = APIRouter(prefix="/admin", tags=["admin"])

_SAFE_AGENT_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,126}$")


class AgentEntryPayload(BaseModel):
    label: str = ""
    role_prompt: str = ""
    skills: List[str] = Field(default_factory=list)


class MultiAgentsPayload(BaseModel):
    max_agents_per_round: int = 2
    max_manager_rounds: int = 4
    agents: Dict[str, AgentEntryPayload]


def _valid_skill_slugs() -> Set[str]:
    return {d.skill_dir.name for d in scan_skills(settings.skills_dir)}


def _normalize_payload(body: MultiAgentsPayload) -> Dict[str, Any]:
    if not body.agents:
        raise HTTPException(status_code=400, detail="至少需要配置一条专线")

    valid_skills = _valid_skill_slugs()
    agents_out: Dict[str, Any] = {}

    for agent_id, entry in body.agents.items():
        aid = agent_id.strip()
        if not _SAFE_AGENT_ID.match(aid):
            raise HTTPException(status_code=400, detail=f"非法专线 id：{agent_id!r}")
        if aid.startswith("_"):
            raise HTTPException(
                status_code=400,
                detail=f"专线 id 不能以 _ 开头：{agent_id!r}",
            )

        seen: Set[str] = set()
        skill_list: List[str] = []
        for s in entry.skills:
            slug = str(s).strip()
            if not slug or slug in seen:
                continue
            if slug not in valid_skills:
                raise HTTPException(
                    status_code=400,
                    detail=f"专线「{aid}」包含不存在或未扫描到的技能：{slug!r}",
                )
            seen.add(slug)
            skill_list.append(slug)

        agents_out[aid] = {
            "label": entry.label.strip(),
            "role_prompt": entry.role_prompt.strip(),
            "skills": skill_list,
        }

    try:
        cap = int(body.max_agents_per_round)
    except (TypeError, ValueError):
        cap = 2
    cap = max(1, min(8, cap))
    try:
        mr = int(body.max_manager_rounds)
    except (TypeError, ValueError):
        mr = 4
    mr = max(1, min(8, mr))

    return {"max_agents_per_round": cap, "max_manager_rounds": mr, "agents": agents_out}


def _response_dict() -> Dict[str, Any]:
    raw = load_registry_dict()
    cap = raw.get("max_agents_per_round", 2)
    try:
        cap_int = max(1, min(8, int(cap)))
    except (TypeError, ValueError):
        cap_int = clamp_max_agents()

    mr = raw.get("max_manager_rounds", 4)
    try:
        mr_int = max(1, min(8, int(mr)))
    except (TypeError, ValueError):
        mr_int = 4

    agents_in = raw.get("agents") or {}
    agents_out: Dict[str, Any] = {}
    if isinstance(agents_in, dict):
        for aid, meta in agents_in.items():
            if not isinstance(meta, dict):
                continue
            skills_raw = meta.get("skills") or []
            skills_list: List[str] = []
            if isinstance(skills_raw, list):
                seen: Set[str] = set()
                for s in skills_raw:
                    slug = str(s).strip()
                    if slug and slug not in seen:
                        seen.add(slug)
                        skills_list.append(slug)
            agents_out[str(aid)] = {
                "label": str(meta.get("label") or "").strip(),
                "role_prompt": str(meta.get("role_prompt") or "").strip(),
                "skills": skills_list,
            }

    return {"max_agents_per_round": cap_int, "max_manager_rounds": mr_int, "agents": agents_out}


@router.get("/multi-agents")
def admin_get_multi_agents(request: Request) -> Dict[str, Any]:
    out = _response_dict()
    log_event(
        request_trace_id(request),
        "admin.multi_agents",
        "listed",
        payload={
            "agent_count": len(out.get("agents") or {}),
            "max_agents_per_round": out.get("max_agents_per_round"),
            "max_manager_rounds": out.get("max_manager_rounds"),
        },
    )
    return out


@router.put("/multi-agents")
def admin_put_multi_agents(body: MultiAgentsPayload, request: Request) -> Dict[str, Any]:
    trace_id = request_trace_id(request)
    normalized = _normalize_payload(body)
    try:
        write_registry_dict(normalized)
    except OSError as exc:
        log_event(
            trace_id,
            "admin.multi_agents",
            "update_failed",
            str(exc),
            level="WARN",
        )
        raise HTTPException(status_code=500, detail="写入 registry 失败") from exc

    out = _response_dict()
    log_event(
        trace_id,
        "admin.multi_agents",
        "updated",
        payload={
            "agent_count": len(normalized.get("agents") or {}),
            "max_agents_per_round": normalized.get("max_agents_per_round"),
            "max_manager_rounds": normalized.get("max_manager_rounds"),
        },
    )
    return out
