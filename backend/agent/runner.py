from __future__ import annotations

import json
import os
import re
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
    skill_args = _skill_args_for_execution(skill_name, plan.get("skill_args", []), messages)
    try:
        script_result = _run_script(skill_doc, skill_args)
    except Exception as exc:
        yield {"type": "error", "content": f"脚本执行失败：{exc}"}
        yield {"type": "done", "content": None}
        return

    yield {"type": "thinking", "content": "正在整理查询结果..."}

    # Step 3: Render results
    text = _response_text(skill_name, plan, script_result)
    yield {"type": "text", "content": text}

    # Step 4: Chart plan
    chart_plan = plan.get("chart_plan")
    if chart_plan and _is_table_result(script_result):
        try:
            option = plan_to_option(chart_plan, script_result)
            yield {"type": "chart", "content": option}
        except Exception as exc:
            yield {"type": "thinking", "content": f"图表生成跳过：{exc}"}

    # Step 5: KPI cards
    kpi_config = plan.get("kpi_cards")
    if kpi_config and _is_table_result(script_result):
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
            **params,
            messages=llm_messages,
            response_format={"type": "json_object"},
            temperature=0.1,
        )
    except Exception as exc:
        raise RuntimeError(f"LLM 调用失败：{type(exc).__name__}: {exc}") from exc

    content = resp.choices[0].message.content
    if content:
        return _parse_json_object(content)

    return None


def _parse_json_object(content: str) -> Dict[str, Any]:
    """Parse model JSON, tolerating fenced JSON blocks."""
    text = content.strip()
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1)
    return json.loads(text)


def _find_skill(skills: List[SkillDoc], name: str) -> Optional[SkillDoc]:
    """Find skill doc by name (case-insensitive partial match)."""
    lower = name.lower()
    for doc in skills:
        if lower in doc.name.lower():
            return doc
    return None


def _latest_user_content(messages: List[Dict[str, str]]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user" and message.get("content"):
            return message["content"]
    return ""


def _skill_args_for_execution(
    skill_name: str, args: List[str], messages: List[Dict[str, str]]
) -> List[str]:
    if "chatbi-semantic-query" in skill_name:
        latest_user = _latest_user_content(messages)
        if latest_user:
            return [latest_user]
    if "chatbi-decision-advisor" in skill_name:
        latest_user = _latest_user_content(messages)
        if latest_user:
            return [latest_user]
    return args


def _run_script(skill: SkillDoc, args: List[str]) -> Any:
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

    merged_env = {**os.environ, **env}
    proc = subprocess.run(
        cmd,
        cwd=str(skill.skill_dir),
        capture_output=True,
        text=True,
        timeout=60,
        env=merged_env,
    )

    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())

    output = proc.stdout.strip()
    if not output:
        return []

    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return []


def _response_text(skill_name: str, plan: Dict[str, Any], result: Any) -> str:
    if "chatbi-semantic-query" in skill_name:
        return _summarize_result(skill_name, result)
    if "chatbi-decision-advisor" in skill_name:
        return _format_decision_advice(result)
    return plan.get("text", "") or _summarize_result(skill_name, result)


def _is_table_result(result: Any) -> bool:
    return isinstance(result, list) and all(isinstance(row, dict) for row in result)


def _summarize_result(skill_name: str, result: Any) -> str:
    """Generate a simple text summary from skill results."""
    if not result:
        return f"「{skill_name}」执行完毕，未返回数据。"
    if not _is_table_result(result):
        return f"「{skill_name}」执行完毕。"
    if len(result) == 1:
        row = result[0]
        parts = [f"{k}: {v}" for k, v in row.items() if v]
        return f"查询完成：{'，'.join(parts)}"
    return f"查询完成，共返回 {len(result)} 条结果。"


def _format_decision_advice(result: Any) -> str:
    if not isinstance(result, dict):
        return _summarize_result("chatbi-decision-advisor", result)

    facts = result.get("facts", {})
    advices = result.get("advices", [])
    overview = facts.get("overview", {}) if isinstance(facts, dict) else {}
    scope = facts.get("scope", {}) if isinstance(facts, dict) else {}
    labels = scope.get("labels", []) if isinstance(scope, dict) else []
    scope_text = "、".join(labels) if labels else "全量数据"

    lines = [
        "## 决策建议",
        "",
        f"- 分析范围：{scope_text}",
    ]
    if overview:
        lines.extend(
            [
                f"- 销售额：{_money(overview.get('sales'))}",
                f"- 目标完成率：{_percent(overview.get('target_achievement_rate'))}",
                f"- 毛利率：{_percent(overview.get('gross_margin_rate'))}",
                f"- 订单数：{overview.get('order_count', '--')}",
                f"- 客户数：{overview.get('customer_count', '--')}",
                "",
            ]
        )

    if not isinstance(advices, list) or not advices:
        lines.append("暂无可输出的规则建议。")
        return "\n".join(lines)

    lines.append("### 建议明细")
    for index, advice in enumerate(advices, start=1):
        if not isinstance(advice, dict):
            continue
        lines.extend(
            [
                "",
                f"{index}. [{advice.get('priority', '中')}] {advice.get('theme', '经营建议')}",
                f"   - 决策：{advice.get('decision', '')}",
                f"   - 依据：{advice.get('reason', '')}",
            ]
        )
        actions = advice.get("actions", [])
        if isinstance(actions, list) and actions:
            lines.append("   - 行动：")
            lines.extend(f"     - {action}" for action in actions)
    return "\n".join(lines)


def _money(value: Any) -> str:
    try:
        return f"{float(value):,.2f}元"
    except (TypeError, ValueError):
        return "--"


def _percent(value: Any) -> str:
    try:
        return f"{float(value) * 100:.2f}%"
    except (TypeError, ValueError):
        return "--"
