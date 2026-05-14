from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

CURRENT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CURRENT_DIR))
sys.path.insert(0, str(CURRENT_DIR.parents[1]))
sys.path.insert(0, str(CURRENT_DIR.parents[2]))

from _shared.output import kpi, skill_response  # noqa: E402
from display_names import domain_display_name  # noqa: E402
from formula_executor import derive_metric, validate_metric_plans  # noqa: E402
from planner import propose_metrics  # noqa: E402
from profile import build_profile  # noqa: E402
from semantic_labels import infer_display_semantics  # noqa: E402


def analyze_from_input(raw: str) -> Dict[str, Any]:
    payload = parse_input(raw)
    question = str(payload.get("question") or payload.get("query") or raw or "")
    rows = [row for row in payload.get("rows", []) if isinstance(row, dict)]
    accepted = [str(item) for item in payload.get("accepted_metric_ids", [])]
    mode = str(payload.get("mode") or infer_mode(question, accepted))
    metric_plans = [item for item in payload.get("metric_plans", []) if isinstance(item, dict)]
    column_labels: Optional[Dict[str, str]] = payload.get("column_labels") or None
    if not isinstance(column_labels, dict):
        column_labels = None
    return execute_analysis(
        question, rows, mode, accepted, metric_plans=metric_plans, column_labels=column_labels
    )


def parse_input(raw: str) -> Dict[str, Any]:
    text = (raw or "").strip()
    if not text:
        return {}
    try:
        loaded = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end <= start:
            return {"question": text, "rows": []}
        try:
            loaded = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return {"question": text, "rows": []}
    return loaded if isinstance(loaded, dict) else {"question": text, "rows": []}


def infer_mode(question: str, accepted: Sequence[str]) -> str:
    text = question or ""
    if accepted or any(word in text for word in ["采纳", "确认", "开始分析", "生成看板"]):
        return "execute"
    return "propose"


def execute_analysis(
    question: str,
    rows: Sequence[Dict[str, Any]],
    mode: str,
    accepted_metric_ids: Sequence[str],
    metric_plans: Sequence[Dict[str, Any]] | None = None,
    column_labels: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    if not rows:
        return skill_response(
            "auto_analysis",
            "需要先读取上传文件并提供可分析的数据行。",
            {"status": "need_clarification", "missing_inputs": ["rows"]},
        )
    profile = build_profile(rows)
    semantic_display = infer_display_semantics(question, profile, column_labels=column_labels)
    merged_column_labels = dict(semantic_display.get("field_labels") or {})
    if column_labels:
        merged_column_labels.update(column_labels)
    profile["domain_label"] = str(
        semantic_display.get("domain_label")
        or domain_display_name(str(profile.get("domain_guess") or ""))
    )
    proposals = validate_metric_plans(
        metric_plans or propose_metrics(question, profile, column_labels=merged_column_labels),
        profile,
    )
    if mode != "execute":
        proposal = build_proposal_payload(question, profile, proposals)
        return skill_response(
            "auto_analysis",
            proposal["markdown"],
            {"status": "need_confirmation", "analysis_proposal": proposal},
        )

    accept_all = any(word in (question or "") for word in ["采纳全部", "全部指标", "全部采纳"])
    selected_ids = (
        set(accepted_metric_ids)
        or extract_requested_metric_ids(question, proposals)
        or (
            {str(item["id"]) for item in proposals}
            if accept_all
            else {str(item["id"]) for item in proposals if item.get("selected")}
        )
    )
    selected = [item for item in proposals if item["id"] in selected_ids]
    if not selected:
        proposal = build_proposal_payload(question, profile, proposals)
        proposal["markdown"] += "\n\n未找到可执行的已选指标，请回复要采纳的指标 ID。"
        return skill_response(
            "auto_analysis",
            proposal["markdown"],
            {"status": "need_confirmation", "analysis_proposal": proposal},
        )

    result_sets = [derive_metric(item, rows) for item in selected]
    result_sets = [item for item in result_sets if item.get("rows")]
    if not result_sets:
        return skill_response(
            "auto_analysis",
            "已识别指标，但当前数据不足以完成计算，请检查字段口径。",
            {"status": "need_clarification", "profile": profile, "metrics": selected},
        )

    charts = [build_chart(metric) for metric in result_sets]
    dashboard = build_dashboard_middleware(question, profile, result_sets, charts)
    return skill_response(
        "auto_analysis",
        dashboard["markdown"],
        {
            "status": "ready",
            "profile": profile,
            "metrics": result_sets,
            "dashboard_middleware": dashboard,
        },
        charts=charts,
        kpis=build_metric_kpis(result_sets),
    )


def build_proposal_payload(
    question: str, profile: Dict[str, Any], proposals: Sequence[Dict[str, Any]]
) -> Dict[str, Any]:
    names = "、".join(item["name"] for item in proposals) or "暂无高置信指标"
    domain_name = str(
        profile.get("domain_label") or domain_display_name(str(profile.get("domain_guess") or ""))
    )
    markdown = (
        f"## 上传表分析建议\n\n"
        f"我根据字段结构识别到 `{profile['row_count']}` 行数据，领域倾向为“{domain_name}”。\n\n"
        f"建议先采纳这些指标：{names}。\n\n"
        "回复 `采纳全部指标`，或回复要采纳的指标 ID，我会继续计算并生成图表与看板。"
    )
    return {
        "markdown": markdown,
        "dataset": {
            "row_count": profile["row_count"],
            "domain_guess": profile["domain_guess"],
            "domain_label": domain_name,
            "confidence": 0.78 if proposals else 0.35,
        },
        "proposed_metrics": list(proposals),
        "actions": [
            {"id": "accept_selected_metrics", "label": "采纳并生成分析", "kind": "primary"},
            {"id": "edit_metrics", "label": "调整指标", "kind": "secondary"},
        ],
        "question": question,
    }


def extract_requested_metric_ids(question: str, proposals: Sequence[Dict[str, Any]]) -> set[str]:
    text = question or ""
    return {str(item["id"]) for item in proposals if str(item["id"]) in text}


def build_chart(metric_result: Dict[str, Any]) -> Dict[str, Any]:
    chart_dir = CURRENT_DIR.parents[1] / "chatbi-chart-recommendation" / "scripts"
    sys.path.insert(0, str(chart_dir))
    from chart_recommendation_core import recommend_chart

    payload = recommend_chart(
        str(metric_result.get("name") or ""),
        metric_result["rows"],
        preferred_chart=str(metric_result.get("chart_hint") or "") or None,
    )
    charts = payload.get("charts") or []
    return charts[0] if charts else {}


def build_dashboard_middleware(
    question: str,
    profile: Dict[str, Any],
    metrics: Sequence[Dict[str, Any]],
    charts: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    dashboard_dir = CURRENT_DIR.parents[1] / "chatbi-dashboard-orchestration" / "scripts"
    sys.path.insert(0, str(dashboard_dir))
    from dashboard_orchestration_core import build_dashboard_package

    payload = build_dashboard_package(
        question,
        {
            "auto_analysis": {
                "profile": profile,
                "metrics": list(metrics),
                "charts": list(charts),
            }
        },
    )
    dashboard = payload.get("data", {}).get("dashboard_middleware")
    if isinstance(dashboard, dict):
        return dashboard
    return {
        "markdown": f"## 上传文件看板已生成\n\n已基于 `{len(metrics)}` 个采纳指标生成图表和看板结构。",
        "title": question if question else "上传文件自动分析看板",
        "dataset": {"row_count": profile["row_count"], "domain_guess": profile["domain_guess"]},
        "widgets": [
            {"id": item["id"], "title": item["name"], "type": "chart", "chart_index": idx}
            for idx, item in enumerate(metrics)
        ],
        "charts": list(charts),
        "metrics": list(metrics),
    }


def build_metric_kpis(metrics: Sequence[Dict[str, Any]]) -> List[Dict[str, str]]:
    cards = [kpi("已生成指标", str(len(metrics)), "个", "success")]
    for item in metrics[:3]:
        cards.append(kpi(item["name"], str(len(item.get("rows", []))), "组", "neutral"))
    return cards
