from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from typing import Any, AsyncGenerator, Dict, List, Optional

from litellm import acompletion

from backend.agent.prompt_builder import SkillDoc, build_system_prompt, scan_skills
from backend.config import settings
from backend.renderers.chart import plan_to_option
from backend.renderers.kpi import build_kpi_cards


async def stream_chat(
    messages: List[Dict[str, str]],
) -> AsyncGenerator[Dict[str, Any], None]:
    """Main agent loop: plan → execute → render → stream SSE events."""
    skills = scan_skills(settings.skills_dir)
    system_prompt = build_system_prompt(skills)

    yield {"type": "thinking", "content": "正在分析您的问题，理解业务语义..."}

    # Step 1: LLM call to generate the action plan
    plan = await _call_llm_for_plan(system_prompt, messages)

    if not plan or not plan.get("skill"):
        # No skill needed, just return text
        yield {"type": "thinking", "content": "正在整理回答..."}
        if plan and plan.get("text"):
            yield {"type": "text", "content": plan["text"]}
        yield {"type": "done", "content": None}
        return

    skill_name = plan["skill"]
    skill_doc = _find_skill(skills, skill_name)
    if not skill_doc:
        yield {"type": "error", "content": f"未找到技能：{skill_name}"}
        yield {"type": "done", "content": None}
        return

    yield {"type": "thinking", "content": f"已选择技能「{skill_name}」"}

    # Step 2: Execute the skill script
    yield {"type": "thinking", "content": f"正在执行 {skill_name}..."}
    try:
        skill_args = plan.get("skill_args") or []
        script_result = _run_script(skill_doc, skill_args)
    except Exception as exc:
        yield {"type": "error", "content": f"脚本执行失败：{exc}"}
        yield {"type": "done", "content": None}
        return

    yield {"type": "thinking", "content": "正在整理查询结果..."}

    # Step 3: Render results — show actual data, fall back to LLM text
    text = _summarize_result(skill_name, script_result) if script_result else plan.get("text", "")
    yield {"type": "text", "content": text}

    # Step 4: Chart plan
    chart_plan = plan.get("chart_plan")
    if chart_plan and script_result:
        try:
            option = plan_to_option(chart_plan, script_result)
            yield {"type": "chart", "content": option}
        except Exception as exc:
            yield {"type": "thinking", "content": f"图表生成跳过：{exc}"}

    # Step 5: KPI cards
    kpi_config = plan.get("kpi_cards")
    if kpi_config:
        try:
            cards = build_kpi_cards(kpi_config, script_result)
            yield {"type": "kpi_cards", "content": cards}
        except Exception as exc:
            yield {"type": "thinking", "content": f"KPI 卡片生成跳过：{exc}"}

    yield {"type": "done", "content": None}


async def _call_llm_for_plan(
    system_prompt: str, messages: List[Dict[str, str]]
) -> Optional[Dict[str, Any]]:
    """Call LLM to produce the action plan as JSON."""
    llm_messages = [
        {"role": "system", "content": system_prompt},
        *messages,
        {"role": "user", "content": "请以 JSON 格式输出你的行动计划。"},
    ]

    try:
        params = settings.llm_params
        resp = await acompletion(
            model=params["model"],
            messages=llm_messages,
            api_key=settings.openai_api_key,
            api_base=params.get("api_base"),
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        content = resp.choices[0].message.content
        if content:
            return json.loads(content)
    except Exception as exc:
        logging.getLogger(__name__).warning("LLM call failed: %s", exc)

    return None


def _find_skill(skills: List[SkillDoc], name: str) -> Optional[SkillDoc]:
    """Find skill doc by name (case-insensitive partial match)."""
    lower = name.lower()
    for doc in skills:
        if lower in doc.name.lower():
            return doc
    return None


def _run_script(skill: SkillDoc, args: List[str]) -> List[Dict[str, str]]:
    """Execute the skill script and parse JSON output."""
    script_dir = skill.skill_dir / "scripts"
    if not script_dir.is_dir():
        raise RuntimeError(f"脚本目录不存在：{script_dir}")

    scripts = list(script_dir.glob("*.py"))
    if not scripts:
        raise RuntimeError(f"未找到 Python 脚本：{script_dir}")

    script_path = scripts[0]
    cmd = [sys.executable, str(script_path), *args, "--json"]

    venv_bin = str(settings.project_root / ".venv" / "Scripts")
    env = {
        "CHATBI_DB_HOST": settings.db_host,
        "CHATBI_DB_PORT": settings.db_port,
        "CHATBI_DB_USER": settings.db_user,
        "CHATBI_DB_PASSWORD": settings.db_password,
        "CHATBI_DB_NAME": settings.db_name,
        "PATH": f"{venv_bin}{os.pathsep}{os.environ.get('PATH', '')}",
    }

    merged_env = {**os.environ, **env, "PYTHONIOENCODING": "utf-8"}
    proc = subprocess.run(
        cmd,
        cwd=str(skill.skill_dir),
        capture_output=True,
        timeout=60,
        env=merged_env,
    )

    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", errors="replace").strip()
        out = proc.stdout.decode("utf-8", errors="replace").strip()
        raise RuntimeError(err or out)

    output = proc.stdout.decode("utf-8", errors="replace").strip()
    if not output:
        return []

    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return []


def _summarize_result(skill_name: str, result: List[Dict[str, str]]) -> str:
    """Generate a simple text summary from skill results."""
    if not result:
        return f"「{skill_name}」执行完毕，未返回数据。"
    if len(result) == 1:
        row = result[0]
        parts = [f"{k}: {v}" for k, v in row.items() if v]
        return f"查询完成：{'，'.join(parts)}"
    return f"查询完成，共返回 {len(result)} 条结果。"
