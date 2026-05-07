from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional

from backend.agent.prompt_builder import SkillDoc
from backend.agent.protocol import normalize_skill_result
from backend.config import settings


def find_skill(skills: List[SkillDoc], name: str) -> Optional[SkillDoc]:
    lower = name.lower()
    for doc in skills:
        if lower in doc.name.lower():
            return doc
    return None


def skill_args_for_execution(
    skill_name: str, args: List[str], messages: List[Dict[str, str]]
) -> List[str]:
    if skill_name in {
        "chatbi-semantic-query",
        "chatbi-decision-advisor",
        "chatbi-semantic-processing",
        "chart-recommendation",
    }:
        latest_user = latest_user_content(messages)
        if latest_user:
            return [latest_user]
    return args


def latest_user_content(messages: List[Dict[str, str]]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user" and message.get("content"):
            return message["content"]
    return ""


def run_script(
    skill: SkillDoc,
    args: List[str],
    trace_id: str = "",
    skill_db_overrides: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    script_dir = skill.skill_dir / "scripts"
    if not script_dir.is_dir():
        raise RuntimeError(f"脚本目录不存在：{script_dir}")

    scripts = sorted(
        script_dir.glob("*.py"),
        key=lambda path: (
            path.name.startswith("_"),
            "core" in path.stem.lower(),
            path.name,
        ),
    )
    if not scripts:
        raise RuntimeError(f"未找到 Python 脚本：{script_dir}")

    cmd = [sys.executable, str(scripts[0]), *args, "--json"]
    proc = subprocess.run(
        cmd,
        cwd=str(skill.skill_dir),
        capture_output=True,
        text=True,
        timeout=60,
        env={**os.environ, **skill_env(trace_id, skill_db_overrides)},
    )

    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())

    output = proc.stdout.strip()
    if not output:
        return {"kind": "empty", "text": "脚本执行完毕，未返回数据。", "data": {}}

    try:
        return normalize_skill_result(json.loads(output), skill.name)
    except json.JSONDecodeError:
        return {"kind": "text", "text": output, "data": {}}


def skill_result_log_payload(result: Dict[str, Any]) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "kind": result.get("kind"),
        "text_preview": str(result.get("text") or "")[:160],
    }
    data = result.get("data")
    if not isinstance(data, dict):
        return payload
    rows = data.get("rows")
    if isinstance(rows, list):
        payload["row_count"] = len(rows)
        if rows and isinstance(rows[0], dict):
            payload["row_keys"] = list(rows[0].keys())[:8]
    query_intent = data.get("query_intent")
    if isinstance(query_intent, dict):
        payload["query_intent"] = {
            "status": query_intent.get("status"),
            "business_line": query_intent.get("business_line"),
            "intent_type": query_intent.get("intent_type"),
            "metric_ids": [
                item.get("metric_id")
                for item in query_intent.get("metrics", [])
                if isinstance(item, dict)
            ][:5],
            "dimension_ids": [
                item.get("dimension_id")
                for item in query_intent.get("dimensions", [])
                if isinstance(item, dict)
            ][:5],
            "missing_slots": query_intent.get("missing_slots", [])[:5],
        }
    if isinstance(data.get("facts"), dict):
        payload["has_facts"] = True
    if isinstance(data.get("advices"), list):
        payload["advice_count"] = len(data["advices"])
    return payload


def skill_env(
    trace_id: str = "",
    db_overrides: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    venv_bin = str(settings.project_root / ".venv" / "Scripts")
    base = {
        "CHATBI_DB_HOST": settings.db_host,
        "CHATBI_DB_PORT": settings.db_port,
        "CHATBI_DB_USER": settings.db_user,
        "CHATBI_DB_PASSWORD": settings.db_password,
        "CHATBI_DB_NAME": settings.db_name,
        "PATH": f"{venv_bin}{os.pathsep}{os.environ.get('PATH', '')}",
        "PYTHONIOENCODING": "utf-8",
        "CHATBI_TRACE_ID": trace_id,
    }
    if db_overrides:
        base.update(db_overrides)
    return base
