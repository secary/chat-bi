"""Accumulate and merge multiple skill execution results for final answers."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.agent.observation import summarize_observation
from backend.renderers.chart import plan_to_option

SkillExecution = Dict[str, Any]

_VISUAL_FIRST_SKILLS = {
    "chatbi-chart-recommendation",
    "chatbi-dashboard-orchestration",
}


def _table_rows(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    data = result.get("data", {})
    if isinstance(data, dict) and isinstance(data.get("rows"), list):
        return data["rows"]
    return []


def sync_skill_sink(
    sink: Optional[Dict[str, Any]],
    last_result: Optional[Dict[str, Any]],
    last_skill_name: Optional[str],
) -> None:
    """Update last pointers without appending execution history (abort / sync paths)."""
    if sink is None:
        return
    sink["last_result"] = last_result
    sink["last_skill_name"] = last_skill_name


def clear_skill_sink(sink: Optional[Dict[str, Any]]) -> None:
    if sink is None:
        return
    sink["skill_executions"] = []
    sink["last_result"] = None
    sink["last_skill_name"] = None


def record_skill_execution(
    sink: Optional[Dict[str, Any]],
    skill: str,
    result: Dict[str, Any],
    step: int,
) -> None:
    if sink is None:
        return
    executions = sink.setdefault("skill_executions", [])
    executions.append(
        {
            "skill": skill,
            "result": result,
            "observation": summarize_observation(skill, result),
            "step": step,
        }
    )
    sink["last_result"] = result
    sink["last_skill_name"] = skill


def get_skill_executions(sink: Optional[Dict[str, Any]]) -> List[SkillExecution]:
    if not sink:
        return []
    raw = sink.get("skill_executions")
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def build_combined_observation(executions: List[SkillExecution]) -> str:
    if not executions:
        return ""
    if len(executions) == 1:
        ex = executions[0]
        return str(ex.get("observation") or "")
    parts: List[str] = []
    for idx, ex in enumerate(executions, start=1):
        skill = str(ex.get("skill") or "skill")
        obs = str(ex.get("observation") or "").strip()
        if obs:
            parts.append(f"## 第 {idx} 次 · {skill}\n{obs}")
    return "\n\n".join(parts)


def _comparison_section_title(result: Dict[str, Any]) -> str:
    data = result.get("data")
    if not isinstance(data, dict):
        return ""
    meta = data.get("comparison_meta")
    if not isinstance(meta, dict):
        return ""
    year = meta.get("year")
    cur = meta.get("cur_month")
    prev = meta.get("prev_month")
    if year and cur and prev:
        return f"{year}年{cur}月 vs {prev}月"
    return ""


def _execution_section_text(skill: str, result: Dict[str, Any]) -> str:
    text = str(result.get("text") or "").strip()
    if skill == "chatbi-comparison":
        title = _comparison_section_title(result)
        if title and text:
            return f"### {title}\n{text}"
        if title:
            return f"### {title}"
    if text:
        return text
    return f"「{skill}」执行完毕。"


def _should_suppress_finish_text(
    last_skill_name: Optional[str],
    merged: Dict[str, Any],
    executions: Optional[List[SkillExecution]] = None,
) -> bool:
    if executions and len(executions) > 1:
        for ex in executions:
            skill = str(ex.get("skill") or "")
            result = ex.get("result")
            if isinstance(result, dict) and _should_suppress_finish_text(skill, result):
                return True
    if last_skill_name not in _VISUAL_FIRST_SKILLS:
        return False
    has_charts = bool(merged.get("charts"))
    has_kpis = bool(merged.get("kpis"))
    return has_charts or has_kpis


def merge_finish_result(
    plan: Dict[str, Any],
    last_result: Optional[Dict[str, Any]],
    last_skill_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Single-execution finish merge (legacy behavior)."""
    merged: Dict[str, Any] = dict(last_result or {})
    if _should_suppress_finish_text(last_skill_name, merged):
        merged["text"] = ""
        return merged
    if last_skill_name == "chatbi-decision-advisor" and merged.get("text"):
        return merged
    if merged.get("chart_plan") or merged.get("charts"):
        return merged
    if plan.get("text"):
        merged["text"] = plan["text"]
    return merged


def _charts_from_execution(ex: SkillExecution) -> List[Dict[str, Any]]:
    result = ex.get("result")
    if not isinstance(result, dict):
        return []
    charts: List[Dict[str, Any]] = []
    for chart in result.get("charts") or []:
        if isinstance(chart, dict):
            charts.append(chart)
    rows = _table_rows(result)
    chart_plan = result.get("chart_plan")
    if isinstance(chart_plan, dict) and rows:
        try:
            charts.append(plan_to_option(chart_plan, rows))
        except Exception:
            pass
    return charts


def _kpis_from_execution(ex: SkillExecution) -> List[Any]:
    result = ex.get("result")
    if not isinstance(result, dict):
        return []
    kpis = result.get("kpis") or []
    return list(kpis) if isinstance(kpis, list) else []


def _merge_multiple_executions(
    executions: List[SkillExecution],
    finish_plan: Dict[str, Any],
    last_skill_name: Optional[str],
) -> Dict[str, Any]:
    last_ex = executions[-1]
    last_result = last_ex.get("result")
    base: Dict[str, Any] = dict(last_result) if isinstance(last_result, dict) else {}

    all_charts: List[Dict[str, Any]] = []
    all_kpis: List[Any] = []
    for ex in executions:
        all_charts.extend(_charts_from_execution(ex))
        all_kpis.extend(_kpis_from_execution(ex))

    merged: Dict[str, Any] = dict(base)
    merged["charts"] = all_charts
    if all_kpis:
        merged["kpis"] = all_kpis
    merged.pop("chart_plan", None)

    if _should_suppress_finish_text(last_skill_name, merged, executions):
        merged["text"] = ""
        return merged

    last_skill = str(last_ex.get("skill") or last_skill_name or "")
    last_skill_result = last_ex.get("result")
    if (
        last_skill == "chatbi-decision-advisor"
        and isinstance(last_skill_result, dict)
        and last_skill_result.get("text")
    ):
        merged["text"] = str(last_skill_result.get("text"))
        return merged

    finish_text = str(finish_plan.get("text") or "").strip()
    if finish_text:
        merged["text"] = finish_text
        return merged

    sections = []
    for ex in executions:
        skill = str(ex.get("skill") or "skill")
        result = ex.get("result")
        if isinstance(result, dict):
            sections.append(_execution_section_text(skill, result))
    merged["text"] = "\n\n".join(s for s in sections if s)
    return merged


def merge_results_for_finish(
    executions: List[SkillExecution],
    finish_plan: Optional[Dict[str, Any]],
    last_skill_name: Optional[str] = None,
) -> Dict[str, Any]:
    plan = finish_plan if isinstance(finish_plan, dict) else {}
    if not executions:
        return dict(plan)
    if len(executions) == 1:
        ex = executions[0]
        result = ex.get("result")
        skill = str(ex.get("skill") or last_skill_name or "")
        if isinstance(result, dict):
            return merge_finish_result(plan, result, skill or last_skill_name)
        return merge_finish_result(plan, None, last_skill_name)
    return _merge_multiple_executions(executions, plan, last_skill_name)
