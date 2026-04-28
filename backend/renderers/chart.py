from __future__ import annotations

from typing import Any, Dict, List


def plan_to_option(
    plan: Dict[str, Any],
    data: List[Dict[str, str]],
) -> Dict[str, Any]:
    """Convert a chart plan + data to an ECharts option dict."""
    chart_type = plan.get("chart_type", "bar")
    dimension_field = plan.get("dimension", "")
    metric_fields: List[str] = plan.get("metrics", [])

    if not data or not dimension_field:
        return _empty_option(chart_type, "暂无数据")

    categories = [_get_value(row, dimension_field) for row in data]

    series = []
    for metric in metric_fields:
        values = [_parse_num(_get_value(row, metric)) for row in data]
        series.append(_build_series(chart_type, metric, values))

    if not series:
        # Auto-detect metric columns from first row
        keys = [k for k in data[0].keys() if k != dimension_field]
        for key in keys:
            values = [_parse_num(_get_value(row, key)) for row in data]
            series.append(_build_series(chart_type, key, values))

    option: Dict[str, Any] = {
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow" if chart_type == "bar" else "cross"}},
        "legend": {"type": "scroll", "bottom": 0},
        "grid": {"left": 60, "right": 24, "bottom": 48, "top": 40, "containLabel": True},
    }

    highlight = plan.get("highlight", {})
    if highlight and "field" in highlight:
        for s in series:
            if s.get("name") == highlight["field"]:
                mode = highlight.get("mode", "max")
                if s.get("data"):
                    s["itemStyle"] = {"color": "#faad14" if mode == "max" else "#ff4d4f"}

    if chart_type == "bar":
        option["xAxis"] = {"type": "category", "data": categories, "axisLabel": {"rotate": 30}}
        option["yAxis"] = {"type": "value"}
        option["series"] = [{**s, "type": "bar"} if "type" not in s else s for s in series]
        if len(series) > 1:
            option["xAxis"]["axisLabel"]["rotate"] = 20

    elif chart_type == "line":
        option["xAxis"] = {"type": "category", "data": categories, "axisLabel": {"rotate": 30}}
        option["yAxis"] = {"type": "value"}
        option["dataZoom"] = [{"type": "inside", "start": 0, "end": 100}]
        option["series"] = [{**s, "type": "line", "smooth": True} if "type" not in s else s for s in series]

    elif chart_type == "pie":
        if series:
            pie_data = [{"name": categories[i], "value": series[0]["data"][i]} for i in range(len(categories))]
            option["series"] = [{
                "type": "pie",
                "radius": ["0%", "70%"],
                "center": ["50%", "55%"],
                "data": pie_data,
                "emphasis": {"itemStyle": {"shadowBlur": 10, "shadowOffsetX": 0, "shadowColor": "rgba(0,0,0,0.5)"}},
                "label": {"formatter": "{b}: {d}%"},
            }]
            del option["tooltip"]["axisPointer"]

    return option


def _build_series(chart_type: str, name: str, values: List[float]) -> Dict[str, Any]:
    series: Dict[str, Any] = {"name": name, "data": values}
    if chart_type in ("bar",):
        series["type"] = "bar"
    elif chart_type in ("line",):
        series["type"] = "line"
    return series


def _get_value(row: Dict[str, str], key: str) -> str:
    return row.get(key, row.get(key.replace("_", ""), ""))


def _parse_num(value: str) -> float:
    try:
        return float(value.replace(",", "").replace("%", ""))
    except (ValueError, AttributeError):
        return 0.0


def _empty_option(chart_type: str, msg: str) -> Dict[str, Any]:
    return {
        "title": {"text": msg, "left": "center"},
        "xAxis": {"type": "category", "data": []},
        "yAxis": {"type": "value"},
        "series": [{"type": chart_type, "data": []}],
    }
