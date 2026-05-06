from __future__ import annotations

import re
from typing import Any, AsyncGenerator, Dict, List

from backend.agent.executor import (
    find_skill,
    latest_user_content,
    run_script,
    skill_args_for_execution,
)
from backend.agent.formatter import stream_result_events
from backend.agent.planner import call_llm_for_plan
from backend.agent.prompt_builder import build_system_prompt, scan_skills
from backend.config import settings
from backend.trace import log_event


DECISION_HINT_RE = re.compile(r"(决策建议|决策意见|经营建议|经营意见|管理建议|管理意见|下一步动作|建议|意见)")
QUERY_HINT_RE = re.compile(
    r"(排行|排名|对比|趋势|汇总|查询|销售额|毛利|毛利率|目标完成率|留存率|客户数|订单数|"
    r"各区域|按区域|按月|按照.*划分|按.*划分|产品|产品类别|渠道|部门|客户类型)"
)
EXPLAIN_HINT_RE = re.compile(r"(口径|解释|是什么意思|什么含义|怎么算|定义|来源)")
METRIC_HINT_RE = re.compile(r"(销售额|毛利|毛利率|目标完成率|客户留存率|客户数|订单数|新增客户数|收入|利润)")
ALIAS_HINT_RE = re.compile(r"(别名|同义词|映射|把.*叫做|新增别名)")


def is_query_plus_decision_request(messages: List[Dict[str, str]]) -> bool:
    latest_user = latest_user_content(messages)
    if not latest_user:
        return False
    return bool(QUERY_HINT_RE.search(latest_user) and DECISION_HINT_RE.search(latest_user))


def infer_metric_name(question: str) -> str:
    metric_patterns = [
        ("目标完成率", ["目标完成率", "完成率", "完成情况"]),
        ("毛利率", ["毛利率", "利润率"]),
        ("毛利", ["毛利", "利润"]),
        ("客户留存率", ["客户留存率", "留存率", "复购"]),
        ("新增客户数", ["新增客户数"]),
        ("客户数", ["客户数"]),
        ("订单数", ["订单数"]),
        ("销售额", ["销售额", "收入", "成交额", "营收"]),
    ]
    for metric_name, words in metric_patterns:
        if any(word in question for word in words):
            return metric_name
    return "销售额"


def infer_dimension_name(question: str) -> str:
    dimension_patterns = [
        ("产品类别", ["产品类别", "产品线", "品类", "产品分类", "产品"]),
        ("产品名称", ["产品名称", "产品名", "具体产品"]),
        ("渠道", ["渠道", "来源渠道", "成交渠道", "获客渠道"]),
        ("部门", ["部门", "团队", "组织"]),
        ("客户类型", ["客户类型", "客群", "客户类别"]),
        ("月份", ["按月", "月份", "月度", "趋势", "时间"]),
        ("区域", ["区域", "大区", "地区", "片区", "市场"]),
    ]
    for dimension_name, words in dimension_patterns:
        if any(word in question for word in words):
            return dimension_name
    return "区域"


def infer_chart_plan(question: str) -> Dict[str, Any]:
    chart_type = "bar"
    if any(word in question for word in ["趋势", "按月", "月份", "月度", "时间"]):
        chart_type = "line"
    elif any(word in question for word in ["占比", "构成", "比例", "贡献"]):
        chart_type = "pie"
    metric_name = infer_metric_name(question)
    dimension_name = infer_dimension_name(question)
    return {
        "chart_type": chart_type,
        "title": f"{dimension_name}{metric_name}分析",
        "dimension": dimension_name,
        "metrics": [metric_name],
        "highlight": {"mode": "max", "field": metric_name},
    }


def build_forced_plan(skill_name: str, question: str) -> Dict[str, Any]:
    plan: Dict[str, Any] = {
        "skill": skill_name,
        "skill_args": [question],
        "steps": [],
        "text": "",
        "chart_plan": None,
        "kpi_cards": [],
    }
    if skill_name == "chatbi-semantic-query":
        plan["chart_plan"] = infer_chart_plan(question)
    return plan


def deterministic_skill_override(messages: List[Dict[str, str]]) -> str:
    latest_user = latest_user_content(messages)
    if not latest_user:
        return ""
    if ALIAS_HINT_RE.search(latest_user):
        return "chatbi-alias-manager"
    if EXPLAIN_HINT_RE.search(latest_user) and METRIC_HINT_RE.search(latest_user):
        return "chatbi-metric-explainer"
    if is_query_plus_decision_request(messages):
        return "chatbi-semantic-query"
    if DECISION_HINT_RE.search(latest_user) and not QUERY_HINT_RE.search(latest_user):
        return "chatbi-decision-advisor"
    if QUERY_HINT_RE.search(latest_user):
        return "chatbi-semantic-query"
    return ""


def should_run_followup_decision_advice(
    plan: Dict[str, Any] | None,
    messages: List[Dict[str, str]],
) -> bool:
    if is_query_plus_decision_request(messages):
        return True
    return bool(plan and plan.get("skill") == "chatbi-semantic-query" and DECISION_HINT_RE.search(latest_user_content(messages)))


def build_execution_steps(
    plan: Dict[str, Any],
    messages: List[Dict[str, str]],
) -> List[Dict[str, Any]]:
    if is_query_plus_decision_request(messages):
        return [
            {
                "skill": "chatbi-semantic-query",
                "skill_args": [latest_user_content(messages)],
                "plan": plan if plan.get("skill") == "chatbi-semantic-query" else {},
                "phase_label": "查询",
            },
            {
                "skill": "chatbi-decision-advisor",
                "skill_args": [latest_user_content(messages)],
                "plan": {},
                "phase_label": "建议",
            },
        ]

    steps = [
        {
            "skill": plan["skill"],
            "skill_args": plan.get("skill_args", []),
            "plan": plan,
            "phase_label": "查询",
        }
    ]
    if should_run_followup_decision_advice(plan, messages):
        steps.append(
            {
                "skill": "chatbi-decision-advisor",
                "skill_args": [latest_user_content(messages)],
                "plan": {},
                "phase_label": "建议",
            }
        )
    return steps


def infer_primary_dimension(result: Dict[str, Any]) -> str:
    data = result.get("data", {})
    rows = data.get("rows") if isinstance(data, dict) else None
    if not isinstance(rows, list) or not rows:
        return ""
    first_row = rows[0]
    if not isinstance(first_row, dict):
        return ""
    keys = list(first_row.keys())
    return keys[0] if len(keys) > 1 else ""


async def stream_chat(
    messages: List[Dict[str, str]],
    trace_id: str = "",
) -> AsyncGenerator[Dict[str, Any], None]:
    """Agent loop: plan, execute one Skill, stream normalized result events."""
    log_event(trace_id, "agent.runner", "started", payload={"message_count": len(messages)})
    skills = scan_skills(settings.skills_dir)
    system_prompt = build_system_prompt(skills)

    yield {"type": "thinking", "content": "正在分析您的问题，理解业务语义..."}
    log_event(trace_id, "agent.planner", "started", payload={"skill_count": len(skills)})
    plan = await call_llm_for_plan(system_prompt, messages)
    forced_skill = deterministic_skill_override(messages)
    if forced_skill and (not plan or plan.get("skill") != forced_skill):
        plan = build_forced_plan(forced_skill, latest_user_content(messages))
    log_event(
        trace_id,
        "agent.planner",
        "completed",
        payload={"skill": plan.get("skill") if plan else None, "forced_skill": forced_skill or None},
    )

    if not plan or not plan.get("skill"):
        log_event(trace_id, "agent.runner", "no_skill")
        yield {"type": "thinking", "content": "正在整理回答..."}
        if plan and plan.get("text"):
            yield {"type": "text", "content": plan["text"]}
        yield {"type": "done", "content": None}
        return

    execution_steps = build_execution_steps(plan, messages)
    if len(execution_steps) > 1:
        yield {"type": "thinking", "content": "识别到您同时需要查询结果和经营建议，开始分两步处理。"}

    previous_result: Dict[str, Any] | None = None
    for step in execution_steps:
        skill_name = step["skill"]
        skill_doc = find_skill(skills, skill_name)
        if not skill_doc:
            log_event(trace_id, "agent.runner", "skill_missing", f"未找到技能：{skill_name}", level="ERROR")
            yield {"type": "error", "content": f"未找到技能：{skill_name}"}
            yield {"type": "done", "content": None}
            return

        yield {"type": "thinking", "content": f"已选择技能「{skill_name}」"}
        if step["phase_label"] == "建议":
            yield {"type": "thinking", "content": "正在基于当前问题生成经营决策建议..."}
        else:
            yield {"type": "thinking", "content": f"正在执行 {skill_name}..."}

        try:
            args = skill_args_for_execution(skill_name, step.get("skill_args", []), messages)
            if skill_name == "chatbi-decision-advisor" and previous_result:
                primary_dimension = infer_primary_dimension(previous_result)
                if primary_dimension and args:
                    args = [f"{args[0]}，重点分析维度：{primary_dimension}"]
            log_event(trace_id, "agent.skill", "started", payload={"skill": skill_name, "args": args})
            result = run_script(skill_doc, args, trace_id=trace_id)
            log_event(
                trace_id,
                "agent.skill",
                "completed",
                payload={"skill": skill_name, "kind": result.get("kind")},
            )
        except Exception as exc:
            log_event(trace_id, "agent.skill", "failed", str(exc), {"skill": skill_name}, "ERROR")
            yield {"type": "error", "content": f"脚本执行失败：{exc}"}
            yield {"type": "done", "content": None}
            return

        if step["phase_label"] == "建议":
            yield {"type": "thinking", "content": "正在整理经营建议..."}
        else:
            yield {"type": "thinking", "content": "正在整理查询结果..."}
        async for event in stream_result_events(skill_name, step["plan"], result):
            yield event
        previous_result = result
    log_event(trace_id, "agent.runner", "completed")
    yield {"type": "done", "content": None}
