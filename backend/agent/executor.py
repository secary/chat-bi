from __future__ import annotations

import json
import os
import re
import sys
from typing import Any, Dict, List, Optional

from backend.agent.prompt_builder import SkillDoc
from backend.agent.protocol import normalize_skill_result
from backend.config import settings

_UPLOAD_PATH_RE = re.compile(r"/tmp/chatbi-uploads/[A-Za-z0-9._-]+", re.IGNORECASE)
_FILE_INGESTION_VALUE_OPTIONS = {"--table", "--sample-size", "--question"}
_FILE_INGESTION_FLAG_OPTIONS = {"--include-rows"}


def find_skill(skills: List[SkillDoc], name: str) -> Optional[SkillDoc]:
    lower = name.lower()
    for doc in skills:
        if lower in doc.name.lower() or lower in doc.skill_dir.name.lower():
            return doc
    return None


def skill_args_for_execution(
    skill_name: str, args: List[str], messages: List[Dict[str, str]]
) -> List[str]:
    if skill_name in {
        "chatbi-semantic-query",
        "chatbi-decision-advisor",
        "chatbi-semantic-processing",
        "chatbi-auto-analysis",
        "chatbi-chart-recommendation",
        "chatbi-dashboard-orchestration",
    }:
        latest_user = latest_user_content(messages)
        if latest_user:
            return [latest_user]
    if skill_name == "chatbi-file-ingestion":
        return file_ingestion_args(args, messages)
    return args


def latest_user_content(messages: List[Dict[str, str]]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user" and message.get("content"):
            return message["content"]
    return ""


def file_ingestion_args(args: List[str], messages: List[Dict[str, str]]) -> List[str]:
    upload_path = first_upload_path(args) or latest_user_upload_path(messages)
    if not upload_path:
        return args
    options = file_ingestion_option_args(args)
    latest_user = latest_user_content(messages)
    if (
        latest_user
        and "--question" not in options
        and _should_pass_question_to_file_ingestion(latest_user)
    ):
        options.extend(["--question", latest_user])
    if _should_include_rows_for_file_followup(messages, args) and "--include-rows" not in options:
        options.append("--include-rows")
    return [upload_path, *options]


def first_upload_path(args: List[str]) -> str:
    for arg in args:
        m = _UPLOAD_PATH_RE.search(str(arg))
        if m:
            return m.group(0)
    return ""


def latest_user_upload_path(messages: List[Dict[str, str]]) -> str:
    for message in reversed(messages):
        if message.get("role") != "user":
            continue
        content = str(message.get("content") or "")
        for m in _UPLOAD_PATH_RE.finditer(content):
            return m.group(0)
    return ""


def option_args(args: List[str]) -> List[str]:
    kept: List[str] = []
    i = 0
    while i < len(args):
        token = str(args[i])
        if token.startswith("--"):
            kept.append(token)
            if i + 1 < len(args) and not str(args[i + 1]).startswith("--"):
                kept.append(str(args[i + 1]))
                i += 1
        i += 1
    return kept


def file_ingestion_option_args(args: List[str]) -> List[str]:
    kept: List[str] = []
    i = 0
    while i < len(args):
        token = str(args[i])
        if token in _FILE_INGESTION_FLAG_OPTIONS:
            kept.append(token)
        elif token in _FILE_INGESTION_VALUE_OPTIONS:
            kept.append(token)
            if i + 1 < len(args) and not str(args[i + 1]).startswith("--"):
                kept.append(str(args[i + 1]))
                i += 1
        i += 1
    return kept


def _should_include_rows_for_file_followup(messages: List[Dict[str, str]], args: List[str]) -> bool:
    text = " ".join([latest_user_content(messages), *[str(arg) for arg in args]]).strip()
    if not text:
        return False
    markers = (
        "画图",
        "图表",
        "可视化",
        "展示",
        "分析",
        "统计",
        "汇总",
        "排行",
        "排名",
        "趋势",
        "对比",
        "分布",
        "占比",
        "比例",
        "百分比",
        "柱状图",
        "折线图",
        "饼图",
        "计算",
        "总计",
        "求和",
        "平均",
        "指标",
        "看板",
        "仪表盘",
        "采纳",
        "确认",
    )
    return any(marker in text for marker in markers)


def _should_pass_question_to_file_ingestion(latest_user: str) -> bool:
    text = str(latest_user or "").strip()
    if not text:
        return False
    markers = (
        "分析",
        "统计",
        "分布",
        "占比",
        "构成",
        "汇总",
        "排行",
        "趋势",
        "对比",
        "字段",
        "指标",
        "看板",
        "仪表盘",
        "采纳",
        "确认",
    )
    return any(marker in text for marker in markers)


def run_script(
    skill: SkillDoc,
    args: List[str],
    trace_id: str = "",
    skill_db_overrides: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    from backend.agent.abort_state import is_aborted

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

    import subprocess as _subprocess

    proc = _subprocess.Popen(
        cmd,
        cwd=str(skill.skill_dir),
        stdout=_subprocess.PIPE,
        stderr=_subprocess.PIPE,
        text=True,
        env={**os.environ, **skill_env(trace_id, skill_db_overrides)},
    )

    # Poll abort in a loop while subprocess runs
    while proc.poll() is None:
        if is_aborted(trace_id):
            proc.kill()
            raise RuntimeError("用户中止了查询")
        import time

        time.sleep(0.1)

    stdout, stderr = proc.communicate()

    if proc.returncode != 0:
        raise RuntimeError(stderr.strip() or stdout.strip())

    output = stdout.strip()
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
