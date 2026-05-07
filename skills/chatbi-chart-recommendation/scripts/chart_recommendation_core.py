from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

CURRENT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CURRENT_DIR.parents[1]))
sys.path.insert(0, str(CURRENT_DIR.parents[2]))

from _shared.output import kpi, skill_response


def recommend_from_input(raw: str) -> Dict[str, Any]:
    question, rows = parse_input(raw)
    return recommend_chart(question, rows)


def parse_input(raw: str) -> Tuple[str, List[Dict[str, Any]]]:
    text = (raw or "").strip()
    if not text:
        return "", []
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return text, []
    if isinstance(payload, dict):
        question = str(payload.get("question") or payload.get("query") or "")
        rows = payload.get("rows")
        if isinstance(rows, list):
            return question, [row for row in rows if isinstance(row, dict)]
        return question, []
    return text, []


def recommend_chart(question: str, rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    row_list = [dict(row) for row in rows if isinstance(row, dict)]
    if not row_list:
        return skill_response(
            kind="chart_recommendation",
            text="图表推荐需要先提供查询结果数据。",
            data={
                "recommendation": {
                    "status": "need_clarification",
                    "analysis_intent": infer_intent(question, []),
                    "reasoning_summary": "当前只有问题，没有可用结果行，无法可靠生成图表。",
                    "missing_inputs": ["rows"],
                }
            },
        )

    dimension, metrics = infer_fields(row_list)
    intent = infer_intent(question, [dimension] if dimension else [])
    if not dimension or not metrics:
        return skill_response(
            kind="chart_recommendation",
            text="这批结果更适合直接展示为表格。",
            data={
                "rows": row_list,
                "recommendation": {
                    "status": "table_only",
                    "analysis_intent": intent,
                    "reasoning_summary": "结果列不足以稳定映射分类维度和数值指标。",
                    "missing_inputs": [],
                },
            },
        )

    if len(row_list) == 1 and len(metrics) == 1:
        metric = metrics[0]
        return skill_response(
            kind="chart_recommendation",
            text=f"推荐使用 KPI 卡片展示 {metric}。",
            data={
                "rows": row_list,
                "recommendation": {
                    "status": "ready",
                    "analysis_intent": "kpi",
                    "recommended_chart": "kpi_card",
                    "reasoning_summary": "单行单指标结果更适合 KPI 卡片。",
                    "confidence": 0.96,
                },
            },
            kpis=[
                kpi(
                    label=metric,
                    value=str(row_list[0].get(metric, "")),
                    unit=infer_unit(metric),
                    status="neutral",
                )
            ],
        )

    chart_plan = build_chart_plan(question, row_list, dimension, metrics, intent)
    option = build_preview_option(chart_plan, row_list)
    return skill_response(
        kind="chart_recommendation",
        text=f"推荐使用{chart_plan['chart_type']}图展示当前结果。",
        data={
            "rows": row_list,
            "recommendation": {
                "status": "ready",
                "analysis_intent": intent,
                "recommended_chart": chart_plan["chart_type"],
                "reasoning_summary": reasoning_summary(intent, dimension, metrics, row_list),
                "confidence": 0.88,
                "dimension": dimension,
                "metrics": metrics[:2],
            },
        },
        charts=[option],
    )


def infer_fields(rows: Sequence[Dict[str, Any]]) -> Tuple[str, List[str]]:
    first = rows[0] if rows else {}
    keys = list(first.keys())
    if len(keys) < 2:
        return "", []
    dimension = keys[0]
    metrics = [key for key in keys[1:] if is_numeric_like(first.get(key))]
    if not metrics:
        metrics = keys[1:2]
    return dimension, metrics[:2]


def infer_intent(question: str, dimensions: Sequence[str]) -> str:
    text = question or ""
    if any(word in text for word in ["趋势", "按月", "变化", "走势"]):
        return "trend"
    if any(word in text for word in ["占比", "构成", "比例", "份额"]):
        return "composition"
    if any(word in text for word in ["排行", "排名", "top"]):
        return "ranking"
    if any(word in text for word in ["对比", "比较", "同比", "环比"]):
        return "comparison"
    if not dimensions:
        return "kpi"
    return "analysis"


def build_chart_plan(
    question: str,
    rows: Sequence[Dict[str, Any]],
    dimension: str,
    metrics: Sequence[str],
    intent: str,
) -> Dict[str, Any]:
    chart_type = "bar"
    if intent == "trend" or dimension in {"月份", "时间", "日期"}:
        chart_type = "line"
    elif intent == "composition" and len(rows) <= 5 and len(metrics) == 1:
        chart_type = "pie"
    return {
        "chart_type": chart_type,
        "title": question or f"{dimension}图表推荐",
        "dimension": dimension,
        "metrics": list(metrics[:2]),
        "highlight": {"mode": "max", "field": metrics[0]},
    }


def build_preview_option(
    plan: Dict[str, Any], rows: Sequence[Dict[str, Any]]
) -> Dict[str, Any]:
    from backend.renderers.chart import plan_to_option

    return plan_to_option(plan, [stringify_row(row) for row in rows])


def stringify_row(row: Dict[str, Any]) -> Dict[str, str]:
    return {key: str(value) if value is not None else "" for key, value in row.items()}


def reasoning_summary(
    intent: str,
    dimension: str,
    metrics: Sequence[str],
    rows: Sequence[Dict[str, Any]],
) -> str:
    if intent == "trend":
        return f"检测到时间趋势场景，按 {dimension} 展示 {metrics[0]} 更容易观察变化。"
    if intent == "composition":
        return f"当前是构成分析场景，类别数为 {len(rows)}，可直接展示 {metrics[0]} 占比。"
    return f"当前结果包含 1 个维度 {dimension} 与 {len(metrics)} 个指标，适合做分类对比。"


def infer_unit(metric: str) -> str:
    if any(word in metric for word in ["率", "%", "占比"]):
        return "%"
    if any(word in metric for word in ["金额", "余额", "收入", "销售额", "毛利"]):
        return "元"
    return ""


def is_numeric_like(value: Any) -> bool:
    if isinstance(value, (int, float)):
        return True
    if value is None:
        return False
    text = str(value).replace(",", "").replace("%", "").strip()
    if not text:
        return False
    try:
        float(text)
        return True
    except ValueError:
        return False
