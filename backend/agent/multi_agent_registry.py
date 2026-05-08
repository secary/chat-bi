"""Load multi-agent registry YAML and resolve enabled skills per agent."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Set

import yaml

from backend.agent.prompt_builder import SkillDoc, scan_skills_enabled
from backend.config import settings


def _registry_path() -> Path:
    return settings.skills_dir / "_agents" / "registry.yaml"


def write_registry_dict(raw: Dict[str, Any]) -> None:
    """Atomically write registry YAML; callers must supply a valid dict shape."""
    path = _registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(
        raw,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    )
    tmp = path.parent / f".{path.name}.tmp"
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def load_registry_dict() -> Dict[str, Any]:
    path = _registry_path()
    if not path.is_file():
        return {"max_agents_per_round": 2, "agents": {}}
    with path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    if not isinstance(raw, dict):
        return {"max_agents_per_round": 2, "agents": {}}
    return raw


def max_agents_per_round() -> int:
    raw = load_registry_dict()
    n = raw.get("max_agents_per_round", 2)
    try:
        return max(1, min(8, int(n)))
    except (TypeError, ValueError):
        return 2


def enabled_slugs() -> Set[str]:
    return {s.skill_dir.name for s in scan_skills_enabled(settings.skills_dir)}


def skills_for_agent(agent_id: str) -> List[SkillDoc]:
    """Intersect registry skills with globally enabled skills."""
    raw = load_registry_dict()
    agents = raw.get("agents") or {}
    if agent_id not in agents or not isinstance(agents[agent_id], dict):
        return []
    slugs = agents[agent_id].get("skills") or []
    if not isinstance(slugs, list):
        return []
    ok = enabled_slugs()
    wanted = [str(s).strip() for s in slugs if str(s).strip() in ok]
    all_docs = scan_skills_enabled(settings.skills_dir)
    by_name = {d.skill_dir.name: d for d in all_docs}
    return [by_name[s] for s in wanted if s in by_name]


def agent_label(agent_id: str) -> str:
    raw = load_registry_dict()
    agents = raw.get("agents") or {}
    entry = agents.get(agent_id)
    if isinstance(entry, dict):
        lab = entry.get("label")
        if isinstance(lab, str) and lab.strip():
            return lab.strip()
    return agent_id


def agent_role_prompt(agent_id: str) -> str:
    raw = load_registry_dict()
    agents = raw.get("agents") or {}
    entry = agents.get(agent_id)
    if isinstance(entry, dict):
        rp = entry.get("role_prompt")
        if isinstance(rp, str) and rp.strip():
            return rp.strip()
    return ""


def list_registry_agent_ids() -> List[str]:
    raw = load_registry_dict()
    agents = raw.get("agents") or {}
    if not isinstance(agents, dict):
        return []
    return list(agents.keys())
