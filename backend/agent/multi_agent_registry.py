"""Load multi-agent registry YAML and resolve preferred / available skills per agent."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Literal, Set

import yaml

from backend.agent.prompt_builder import SkillDoc, scan_skills_enabled
from backend.config import settings

SkillMode = Literal["dynamic", "restricted"]


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
        return {"max_agents_per_round": 2, "max_manager_rounds": 4, "agents": {}}
    with path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    if not isinstance(raw, dict):
        return {"max_agents_per_round": 2, "max_manager_rounds": 4, "agents": {}}
    return raw


def max_agents_per_round() -> int:
    raw = load_registry_dict()
    n = raw.get("max_agents_per_round", 2)
    try:
        return max(1, min(8, int(n)))
    except (TypeError, ValueError):
        return 2


def max_manager_rounds() -> int:
    """Manager LLM planning iterations (1 = legacy single-shot). Clamped 1–8."""
    raw = load_registry_dict()
    n = raw.get("max_manager_rounds", 4)
    try:
        return max(1, min(8, int(n)))
    except (TypeError, ValueError):
        return 4


def enabled_slugs() -> Set[str]:
    return {s.skill_dir.name for s in scan_skills_enabled(settings.skills_dir)}


def agent_enabled(agent_id: str) -> bool:
    raw = load_registry_dict()
    agents = raw.get("agents") or {}
    if agent_id not in agents or not isinstance(agents[agent_id], dict):
        return False
    value = agents[agent_id].get("enabled")
    if isinstance(value, bool):
        return value
    return True


def agent_skill_mode(agent_id: str) -> SkillMode:
    raw = load_registry_dict()
    agents = raw.get("agents") or {}
    if agent_id not in agents or not isinstance(agents[agent_id], dict):
        return "dynamic"
    mode = str(agents[agent_id].get("skill_mode") or "dynamic").strip().lower()
    return "restricted" if mode == "restricted" else "dynamic"


def preferred_skill_slugs_for_agent(agent_id: str) -> List[str]:
    raw = load_registry_dict()
    agents = raw.get("agents") or {}
    if agent_id not in agents or not isinstance(agents[agent_id], dict):
        return []
    slugs = agents[agent_id].get("skills") or []
    if not isinstance(slugs, list):
        return []
    ok = enabled_slugs()
    seen: Set[str] = set()
    out: List[str] = []
    for slug in slugs:
        name = str(slug).strip()
        if name and name in ok and name not in seen:
            seen.add(name)
            out.append(name)
    return out


def blocked_skill_slugs_for_agent(agent_id: str) -> List[str]:
    raw = load_registry_dict()
    agents = raw.get("agents") or {}
    if agent_id not in agents or not isinstance(agents[agent_id], dict):
        return []
    slugs = agents[agent_id].get("blocked_skills") or []
    if not isinstance(slugs, list):
        return []
    ok = enabled_slugs()
    seen: Set[str] = set()
    out: List[str] = []
    for slug in slugs:
        name = str(slug).strip()
        if name and name in ok and name not in seen:
            seen.add(name)
            out.append(name)
    return out


def skills_for_agent(agent_id: str) -> List[SkillDoc]:
    """Resolve runtime skills. Dynamic mode may use any enabled skill except blocked ones."""
    all_docs = scan_skills_enabled(settings.skills_dir)
    by_name = {d.skill_dir.name: d for d in all_docs}
    preferred = preferred_skill_slugs_for_agent(agent_id)
    blocked = set(blocked_skill_slugs_for_agent(agent_id))
    mode = agent_skill_mode(agent_id)

    if mode == "restricted":
        wanted = [slug for slug in preferred if slug not in blocked]
        return [by_name[slug] for slug in wanted if slug in by_name]

    preferred_docs = [
        by_name[slug] for slug in preferred if slug in by_name and slug not in blocked
    ]
    preferred_names = {doc.skill_dir.name for doc in preferred_docs}
    rest_docs = [
        doc
        for doc in all_docs
        if doc.skill_dir.name not in blocked and doc.skill_dir.name not in preferred_names
    ]
    return preferred_docs + rest_docs


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
    return [str(agent_id) for agent_id in agents.keys() if agent_enabled(str(agent_id))]


def list_all_registry_agent_ids() -> List[str]:
    raw = load_registry_dict()
    agents = raw.get("agents") or {}
    if not isinstance(agents, dict):
        return []
    return [str(agent_id) for agent_id in agents.keys()]
