from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

CURRENT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CURRENT_DIR.parents[1]))
sys.path.insert(0, str(CURRENT_DIR.parents[2]))

from _shared.output import kpi, skill_response  # noqa: E402


def recommend_from_input(raw: str) -> Dict[str, Any]:
    question, rows, preferred_chart = parse_input(raw)
    return recommend_chart(question, rows, preferred_chart=preferred_chart)


def parse_input(raw: str) -> Tuple[str, List[Dict[str, Any]], Optional[str]]:
    text = (raw or "").strip()
    if not text:
        return "", [], None
    payload = _extract_payload(text)
    if payload is None:
        return text, [], None
    if isinstance(payload, dict):
        question = str(payload.get("question") or payload.get("query") or "")
        preferred_chart = payload.get("preferred_chart")
        rows = payload.get("rows")
        if isinstance(rows, list):
            return (
                question,
                [row for row in rows if isinstance(row, dict)],
                str(preferred_chart) if preferred_chart else None,
            )
        return question, [], str(preferred_chart) if preferred_chart else None
    return text, [], None


def _extract_payload(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    candidate = text[start : end + 1]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


def recommend_chart(
    question: str,
    rows: Sequence[Dict[str, Any]],
    preferred_chart: Optional[str] = None,
) -> Dict[str, Any]:
    row_list = [dict(row) for row in rows if isinstance(row, dict)]
    if not row_list:
        return skill_response(
            kind="chart_recommendation",
            text="图表推荐需要先提供查询结果数据。",
            data={
                "recommendation": {
                    "status": "need_clarification",
                    "analysis_intent": infer_intent(question, {"shape": "table_only"}),
                    "reasoning_summary": "当前只有问题，没有可用结果行，无法可靠生成图表。",
                    "missing_inputs": ["rows"],
                }
            },
        )

    shape = analyze_shape(row_list)
    intent = infer_intent(question, shape)
    if shape["shape"] == "table_only":
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

    if shape["shape"] == "single_metric":
        metric = shape["metrics"][0]
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

    chart_plan = build_chart_plan(
        question, row_list, shape, intent, preferred_chart=preferred_chart
    )
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
                "reasoning_summary": reasoning_summary(intent, shape, row_list),
                "confidence": 0.88,
                "dimension": shape.get("primary_dimension") or "",
                "metrics": shape.get("metrics", [])[:3],
            },
        },
        charts=[option],
    )


def infer_intent(question: str, shape: Dict[str, Any]) -> str:
    text = question or ""
    if any(word in text for word in ["漏斗", "转化", "转化率"]) or shape.get("shape") == "funnel":
        return "funnel"
    if any(word in text for word in ["趋势", "按月", "变化", "走势"]):
        return "trend"
    if any(word in text for word in ["占比", "构成", "比例", "份额", "结构"]):
        return "composition"
    if any(word in text for word in ["分布", "离散", "波动", "异常值"]):
        return "distribution"
    if any(word in text for word in ["排行", "排名", "top"]):
        return "ranking"
    if any(word in text for word in ["对比", "比较", "同比", "环比"]):
        return "comparison"
    if shape.get("shape") == "matrix":
        return "matrix"
    if shape.get("shape") == "two_metrics":
        return "relationship"
    if shape.get("shape") == "category_by_time":
        return "trend"
    if shape.get("shape") == "multi_metric_by_time":
        return "trend"
    if shape.get("shape") == "metric_by_time":
        return "trend"
    if shape.get("shape") in {"metric_by_category", "ranked_category"}:
        return "ranking" if _looks_like_ranking(shape) else "comparison"
    if shape.get("shape") == "single_metric":
        return "kpi"
    return "analysis"


def build_chart_plan(
    question: str,
    rows: Sequence[Dict[str, Any]],
    shape: Dict[str, Any],
    intent: str,
    preferred_chart: Optional[str] = None,
) -> Dict[str, Any]:
    metrics = list(shape.get("metrics", []))
    dimensions = list(shape.get("dimensions", []))
    primary_dimension = str(shape.get("primary_dimension") or "")
    secondary_dimension = str(shape.get("secondary_dimension") or "")
    chart_type = select_chart_type(shape, intent, question, preferred_chart)
    return {
        "chart_type": chart_type,
        "title": question or f"{primary_dimension or '分析'}图表推荐",
        "dimension": primary_dimension,
        "dimensions": dimensions,
        "secondary_dimension": secondary_dimension,
        "metrics": metrics[:3],
        "highlight": {"mode": "max", "field": metrics[0]} if metrics else {},
    }


def build_preview_option(plan: Dict[str, Any], rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    from backend.renderers.chart import plan_to_option

    return plan_to_option(plan, [stringify_row(row) for row in rows])


def stringify_row(row: Dict[str, Any]) -> Dict[str, str]:
    return {key: str(value) if value is not None else "" for key, value in row.items()}


def reasoning_summary(
    intent: str,
    shape: Dict[str, Any],
    rows: Sequence[Dict[str, Any]],
) -> str:
    metrics = list(shape.get("metrics", []))
    dimension = str(shape.get("primary_dimension") or "")
    if intent == "trend":
        return f"检测到时间趋势场景，按 {dimension} 展示 {metrics[0]} 更容易观察变化。"
    if intent == "composition":
        return f"当前是构成分析场景，类别数为 {len(rows)}，可直接展示 {metrics[0]} 占比。"
    if intent == "distribution":
        return f"当前更接近分布分析场景，先用分类分布图展示 {metrics[0]} 在 {dimension} 上的差异。"
    if intent == "relationship":
        return f"当前结果包含两个数值指标，适合观察 {metrics[0]} 与 {metrics[1]} 的关系。"
    if intent == "matrix":
        return "当前结果包含两个分类维度与一个指标，适合用热力矩阵查看强弱分布。"
    if intent == "funnel":
        return "当前结果呈现业务阶段流转关系，适合用漏斗图展示各阶段转化。"
    return f"当前结果包含 1 个维度 {dimension} 与 {len(metrics)} 个指标，适合做分类对比。"


def _should_use_pie(
    rows: Sequence[Dict[str, Any]],
    metrics: Sequence[str],
    intent: str,
    question: str,
    preferred_chart: Optional[str],
) -> bool:
    if preferred_chart == "pie":
        return (
            len(rows) >= 2
            and len(rows) <= 6
            and len(metrics) == 1
            and _all_non_negative(rows, metrics[0])
        )
    if intent not in {"composition", "distribution"}:
        return False
    if len(rows) < 2 or len(rows) > 5 or len(metrics) != 1:
        return False
    if any(word in (question or "") for word in ["趋势", "排行", "排名"]):
        return False
    return _all_non_negative(rows, metrics[0])


def _all_non_negative(rows: Sequence[Dict[str, Any]], metric: str) -> bool:
    for row in rows:
        value = row.get(metric)
        if not is_numeric_like(value):
            return False
        if float(str(value).replace(",", "").replace("%", "").strip()) < 0:
            return False
    return True


def analyze_shape(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    if not rows:
        return {"shape": "table_only", "dimensions": [], "metrics": [], "row_count": 0}
    row_count = len(rows)
    keys = list(rows[0].keys())
    metrics = [
        key
        for key in keys
        if all(is_numeric_like(row.get(key)) for row in rows[: min(20, len(rows))])
    ]
    dimensions = [key for key in keys if key not in metrics]
    time_dimensions = [key for key in dimensions if _is_time_field(key, rows)]
    category_dimensions = [key for key in dimensions if key not in time_dimensions]

    if len(rows) == 1 and len(metrics) == 1:
        return {
            "shape": "single_metric",
            "metrics": metrics,
            "dimensions": dimensions,
            "row_count": row_count,
        }
    if len(rows) == 1 and len(metrics) >= 3 and _looks_like_funnel_metrics(metrics):
        return {
            "shape": "funnel",
            "metrics": metrics,
            "dimensions": dimensions,
            "primary_dimension": dimensions[0] if dimensions else "",
            "row_count": row_count,
        }
    if (
        len(category_dimensions) >= 1
        and len(metrics) == 1
        and _looks_like_funnel_stage_rows(rows, category_dimensions[0])
    ):
        return {
            "shape": "funnel",
            "metrics": metrics,
            "dimensions": dimensions,
            "primary_dimension": category_dimensions[0],
            "row_count": row_count,
        }
    if time_dimensions and len(metrics) == 1 and not category_dimensions:
        return {
            "shape": "metric_by_time",
            "metrics": metrics,
            "dimensions": dimensions,
            "primary_dimension": time_dimensions[0],
            "row_count": row_count,
        }
    if time_dimensions and len(metrics) >= 2 and not category_dimensions:
        return {
            "shape": "multi_metric_by_time",
            "metrics": metrics,
            "dimensions": dimensions,
            "primary_dimension": time_dimensions[0],
            "row_count": row_count,
        }
    if time_dimensions and category_dimensions and len(metrics) == 1:
        return {
            "shape": "category_by_time",
            "metrics": metrics,
            "dimensions": dimensions,
            "primary_dimension": time_dimensions[0],
            "secondary_dimension": category_dimensions[0],
            "row_count": row_count,
        }
    if len(category_dimensions) >= 2 and len(metrics) == 1:
        return {
            "shape": "matrix",
            "metrics": metrics,
            "dimensions": dimensions,
            "primary_dimension": category_dimensions[0],
            "secondary_dimension": category_dimensions[1],
            "row_count": row_count,
        }
    if len(category_dimensions) >= 1 and len(metrics) >= 2:
        return {
            "shape": "comparison",
            "metrics": metrics,
            "dimensions": dimensions,
            "primary_dimension": category_dimensions[0],
            "row_count": row_count,
        }
    if len(category_dimensions) >= 1 and len(metrics) == 1:
        return {
            "shape": "metric_by_category",
            "metrics": metrics,
            "dimensions": dimensions,
            "primary_dimension": category_dimensions[0],
            "row_count": row_count,
        }
    if len(metrics) >= 2:
        return {
            "shape": "two_metrics",
            "metrics": metrics[:3],
            "dimensions": dimensions,
            "primary_dimension": dimensions[0] if dimensions else "",
            "row_count": row_count,
        }
    return {
        "shape": "table_only",
        "metrics": metrics,
        "dimensions": dimensions,
        "primary_dimension": dimensions[0] if dimensions else "",
        "row_count": row_count,
    }


def select_chart_type(
    shape: Dict[str, Any],
    intent: str,
    question: str,
    preferred_chart: Optional[str],
) -> str:
    if preferred_chart:
        return preferred_chart
    shape_name = str(shape.get("shape") or "")
    metrics = list(shape.get("metrics", []))
    if shape_name == "funnel":
        return "funnel"
    if _should_use_pie_for_shape(shape, intent, question):
        return "pie"
    if shape_name == "metric_by_time":
        return "line"
    if shape_name == "multi_metric_by_time":
        return "multi_line"
    if shape_name == "category_by_time":
        return "stacked_bar"
    if shape_name == "matrix":
        return "heatmap"
    if shape_name == "comparison":
        return "grouped_bar"
    if shape_name == "two_metrics":
        return "scatter"
    if shape_name == "metric_by_category":
        return "horizontal_bar" if _looks_like_ranking(shape) else "bar"
    if shape_name == "single_metric":
        return "kpi_card"
    return "bar" if metrics else "table"


def _should_use_pie_for_shape(shape: Dict[str, Any], intent: str, question: str) -> bool:
    if shape.get("shape") != "metric_by_category":
        return False
    metrics = list(shape.get("metrics", []))
    if len(metrics) != 1:
        return False
    row_count = int(shape.get("row_count") or 0)
    if row_count and not (2 <= row_count <= 5):
        return False
    if any(word in (question or "") for word in ["趋势", "排行", "排名"]):
        return False
    return intent in {"composition", "distribution"}


def _looks_like_ranking(shape: Dict[str, Any]) -> bool:
    dimension = str(shape.get("primary_dimension") or "")
    row_count = int(shape.get("row_count") or 0)
    return row_count > 5 or len(dimension) > 4


def _is_time_field(field: str, rows: Sequence[Dict[str, Any]]) -> bool:
    if any(token in field.lower() for token in ["month", "date", "time", "year"]):
        return True
    sample = str(rows[0].get(field, "")) if rows else ""
    return len(sample) >= 7 and sample[4:5] == "-"


def _looks_like_funnel_metrics(metrics: Sequence[str]) -> bool:
    joined = " ".join(item.lower() for item in metrics)
    keywords = [
        "lead",
        "qualified",
        "proposal",
        "won",
        "lost",
        "closed",
        "线索",
        "意向",
        "方案",
        "成交",
        "流失",
    ]
    return sum(1 for token in keywords if token in joined) >= 3


def _looks_like_funnel_stage_rows(rows: Sequence[Dict[str, Any]], dimension: str) -> bool:
    if not rows:
        return False
    dimension_name = dimension.lower()
    if any(token in dimension_name for token in ["stage", "阶段", "环节", "漏斗"]):
        return True
    labels = " ".join(str(row.get(dimension, "")).lower() for row in rows[: min(8, len(rows))])
    keywords = [
        "lead",
        "qualified",
        "proposal",
        "won",
        "lost",
        "closed",
        "线索",
        "有效",
        "方案",
        "商机",
        "成交",
        "流失",
    ]
    return sum(1 for token in keywords if token in labels) >= 3


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
