from __future__ import annotations

from typing import Dict, Optional, Sequence

from _shared.output import kpi, skill_response

from .models import SemanticPlan


def is_nullish(value: object) -> bool:
    if value is None:
        return True
    text = str(value).strip()
    return text == "" or text.upper() == "NULL"


def is_rate_metric(metric_name: str) -> bool:
    return any(word in metric_name for word in ["率", "占比", "比例", "份额"])


def format_metric_value(metric_name: str, value: object) -> tuple[str, str]:
    text = str(value).strip()
    if is_rate_metric(metric_name):
        try:
            numeric = float(text) * 100
            return f"{numeric:.2f}", "%"
        except ValueError:
            return text, ""
    return text, ""


def build_single_value_kpis(rows: Sequence[Dict[str, str]]) -> list[Dict[str, str]]:
    if len(rows) != 1:
        return []
    columns = list(rows[0].keys())
    if len(columns) == 1:
        metric_name = columns[0]
    elif len(columns) == 2:
        # Single-row grouped results such as "渠道=线上, 销售额=700000" are
        # still effectively a single-value summary and should render as KPI
        # instead of a one-bar chart.
        metric_name = columns[1]
    else:
        return []
    raw_value = rows[0].get(metric_name)
    if is_nullish(raw_value):
        return []
    value, unit = format_metric_value(metric_name, raw_value)
    return [kpi(label=metric_name, value=value, unit=unit, status="neutral")]


def print_table(rows: Sequence[Dict[str, str]]) -> None:
    if not rows:
        print("(no rows)")
        return
    headers = list(rows[0].keys())
    widths = {
        header: max(len(header), *(len(str(row.get(header, ""))) for row in rows))
        for header in headers
    }
    print(" | ".join(header.ljust(widths[header]) for header in headers))
    print("-+-".join("-" * widths[header] for header in headers))
    for row in rows:
        print(" | ".join(str(row.get(header, "")).ljust(widths[header]) for header in headers))


def response_text(rows: Sequence[Dict[str, str]]) -> str:
    if not rows:
        return "查询完成，未返回数据。"
    if len(rows) == 1 and all(is_nullish(value) for value in rows[0].values()):
        return "查询完成，未返回数据。"
    if len(rows) == 1:
        parts = []
        for key, value in rows[0].items():
            if is_nullish(value):
                continue
            rendered_value, unit = format_metric_value(key, value)
            parts.append(f"{key}: {rendered_value}{unit}")
        return f"查询完成：{'，'.join(parts)}"
    return f"查询完成，共返回 {len(rows)} 条结果。"


def infer_chart_plan(question: str, rows: Sequence[Dict[str, str]]) -> Optional[Dict[str, object]]:
    if not rows:
        return None
    columns = list(rows[0].keys())
    if len(columns) < 2:
        return None

    dimension = columns[0]
    metrics = [col for col in columns[1:]]
    if not metrics:
        return None

    # A single row with one metric is better expressed as a KPI summary.
    if len(rows) == 1 and len(metrics) == 1:
        return None

    if any(word in question for word in ["占比", "构成", "贡献", "比例", "份额"]):
        chart_type = "pie"
    elif any(word in question for word in ["趋势", "变化", "按月", "时间"]) or dimension in (
        "月份",
        "时间",
    ):
        chart_type = "line"
    else:
        chart_type = "bar"

    return {
        "chart_type": chart_type,
        "title": question,
        "dimension": dimension,
        "metrics": metrics[:2],
        "highlight": {"mode": "max", "field": metrics[0]},
    }


def build_plan_summary(plan: SemanticPlan) -> Dict[str, object]:
    return {
        "metric": plan.metric.name,
        "metric_code": plan.metric.code,
        "source_table": plan.metric.table,
        "dimensions": [dim.name for dim in plan.dimensions],
        "filters": [{"dimension": dim_name, "value": value} for dim_name, value, _ in plan.filters],
        "time_filter": plan.time_filter[1] if plan.time_filter else None,
        "order_by_metric_desc": plan.order_by_metric_desc,
        "limit": plan.limit,
    }


def build_plan_trace(plan: SemanticPlan) -> list[str]:
    steps = [f"收到问数请求：{plan.question}"]
    if plan.time_filter:
        steps.append(f"识别时间范围：{plan.time_filter[1]}")
    else:
        steps.append("未识别显式时间范围，按默认口径查询。")

    steps.append(
        f"识别指标：{plan.metric.name}（来源表 {plan.metric.table}，编码 {plan.metric.code}）"
    )

    if plan.dimensions:
        steps.append(f"识别维度：{'、'.join(dim.name for dim in plan.dimensions)}")
    else:
        steps.append("未识别分组维度，按单值汇总查询。")

    if plan.filters:
        rendered_filters = "，".join(f"{dim_name}={value}" for dim_name, value, _ in plan.filters)
        steps.append(f"识别过滤条件：{rendered_filters}")
    else:
        steps.append("未识别额外过滤条件。")

    if plan.order_by_metric_desc:
        steps.append(f"识别排序需求：按{plan.metric.name}从高到低排行。")
    else:
        steps.append("未识别排序需求。")

    if plan.limit is not None:
        steps.append(f"识别结果条数限制：返回前 {plan.limit} 条。")

    steps.append(f"生成 SQL：{plan.sql}")
    return steps


def build_json_payload(
    question: str,
    sql: str,
    rows: Sequence[Dict[str, str]],
    plan: Optional[SemanticPlan] = None,
) -> Dict[str, object]:
    data: Dict[str, object] = {"question": question, "sql": sql, "rows": list(rows)}
    if plan is not None:
        data["plan_summary"] = build_plan_summary(plan)
        data["plan_trace"] = build_plan_trace(plan)
    payload = skill_response(
        kind="table",
        text=response_text(rows),
        data=data,
        kpis=build_single_value_kpis(rows),
    )
    chart_plan = infer_chart_plan(question, rows)
    if chart_plan:
        payload["chart_plan"] = chart_plan
    return payload
