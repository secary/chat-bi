from __future__ import annotations

from typing import Any, Dict, List


def plan_to_option(
    plan: Dict[str, Any],
    data: List[Dict[str, str]],
) -> Dict[str, Any]:
    """Convert a chart plan + data to an ECharts option dict."""
    chart_type = plan.get("chart_type", "bar")
    dimension_field = str(plan.get("dimension") or "")
    dimensions: List[str] = plan.get("dimensions", []) or []
    secondary_dimension = str(plan.get("secondary_dimension") or "")
    metric_fields: List[str] = plan.get("metrics", []) or []

    if data and (not dimension_field or not metric_fields):
        inferred_dimension, inferred_metrics = _infer_fields_from_rows(data)
        if not dimension_field:
            dimension_field = inferred_dimension
        if not metric_fields:
            metric_fields = inferred_metrics

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
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "shadow" if chart_type == "bar" else "cross"},
        },
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

    elif chart_type == "horizontal_bar":
        option["xAxis"] = {"type": "value"}
        option["yAxis"] = {"type": "category", "data": categories}
        option["series"] = [{**s, "type": "bar"} if "type" not in s else s for s in series]

    elif chart_type == "grouped_bar":
        option["xAxis"] = {"type": "category", "data": categories, "axisLabel": {"rotate": 20}}
        option["yAxis"] = {"type": "value"}
        option["series"] = [{**s, "type": "bar"} if "type" not in s else s for s in series]

    elif chart_type == "stacked_bar":
        if secondary_dimension and dimension_field and metric_fields:
            matrix = _pivot_rows(data, dimension_field, secondary_dimension, metric_fields[0])
            option["xAxis"] = {
                "type": "category",
                "data": matrix["categories"],
                "axisLabel": {"rotate": 20},
            }
            option["yAxis"] = {"type": "value"}
            option["series"] = [
                {"name": name, "type": "bar", "stack": "total", "data": values}
                for name, values in matrix["series"]
            ]
        else:
            option["xAxis"] = {"type": "category", "data": categories, "axisLabel": {"rotate": 20}}
            option["yAxis"] = {"type": "value"}
            option["series"] = [
                (
                    {**s, "type": "bar", "stack": "total"}
                    if "type" not in s
                    else {**s, "stack": "total"}
                )
                for s in series
            ]

    elif chart_type == "line":
        option["xAxis"] = {"type": "category", "data": categories, "axisLabel": {"rotate": 30}}
        option["yAxis"] = {"type": "value"}
        option["dataZoom"] = [{"type": "inside", "start": 0, "end": 100}]
        option["series"] = [
            {**s, "type": "line", "smooth": True} if "type" not in s else s for s in series
        ]

    elif chart_type == "multi_line":
        option["xAxis"] = {"type": "category", "data": categories, "axisLabel": {"rotate": 20}}
        option["yAxis"] = {"type": "value"}
        option["dataZoom"] = [{"type": "inside", "start": 0, "end": 100}]
        option["series"] = [
            {**s, "type": "line", "smooth": True} if "type" not in s else s for s in series
        ]

    elif chart_type == "area":
        option["xAxis"] = {"type": "category", "data": categories, "axisLabel": {"rotate": 20}}
        option["yAxis"] = {"type": "value"}
        option["series"] = [
            (
                {**s, "type": "line", "smooth": True, "areaStyle": {}}
                if "type" not in s
                else {**s, "areaStyle": {}}
            )
            for s in series
        ]

    elif chart_type == "pie":
        if series:
            pie_data = [
                {"name": categories[i], "value": series[0]["data"][i]}
                for i in range(len(categories))
            ]
            option["series"] = [
                {
                    "type": "pie",
                    "radius": ["0%", "70%"],
                    "center": ["50%", "55%"],
                    "data": pie_data,
                    "emphasis": {
                        "itemStyle": {
                            "shadowBlur": 10,
                            "shadowOffsetX": 0,
                            "shadowColor": "rgba(0,0,0,0.5)",
                        }
                    },
                    "label": {"formatter": "{b}: {d}%"},
                }
            ]
            del option["tooltip"]["axisPointer"]

    elif chart_type == "scatter":
        if len(metric_fields) >= 2:
            x_metric, y_metric = metric_fields[:2]
            option["xAxis"] = {"type": "value", "name": x_metric}
            option["yAxis"] = {"type": "value", "name": y_metric}
            option["series"] = [
                {
                    "type": "scatter",
                    "data": [
                        [
                            _parse_num(_get_value(row, x_metric)),
                            _parse_num(_get_value(row, y_metric)),
                            _get_value(row, dimension_field) if dimension_field else "",
                        ]
                        for row in data
                    ],
                }
            ]
            option["tooltip"]["trigger"] = "item"

    elif chart_type == "heatmap":
        y_dimension = secondary_dimension or (dimensions[1] if len(dimensions) > 1 else "")
        metric = metric_fields[0] if metric_fields else ""
        if dimension_field and y_dimension and metric:
            matrix = _heatmap_matrix(data, dimension_field, y_dimension, metric)
            option["xAxis"] = {"type": "category", "data": matrix["x"]}
            option["yAxis"] = {"type": "category", "data": matrix["y"]}
            option["visualMap"] = {
                "min": matrix["min"],
                "max": matrix["max"],
                "calculable": True,
                "orient": "horizontal",
                "left": "center",
                "bottom": 0,
            }
            option["series"] = [
                {
                    "type": "heatmap",
                    "data": matrix["data"],
                    "label": {"show": True},
                }
            ]

    elif chart_type == "funnel":
        if metric_fields:
            option["tooltip"]["trigger"] = "item"
            option["legend"] = {"show": False}
            if dimension_field and len(metric_fields) == 1 and len(data) >= 2:
                metric = metric_fields[0]
                funnel_data = [
                    {
                        "name": _get_value(row, dimension_field),
                        "value": _parse_num(_get_value(row, metric)),
                    }
                    for row in data
                ]
            else:
                funnel_data = [
                    {"name": metric, "value": _parse_num(_get_value(data[0], metric))}
                    for metric in metric_fields
                ]
            option["series"] = [
                {
                    "type": "funnel",
                    "left": "10%",
                    "top": 20,
                    "bottom": 20,
                    "width": "80%",
                    "sort": "descending",
                    "gap": 4,
                    "label": {"show": True, "position": "inside"},
                    "data": funnel_data,
                }
            ]

    return option


def _build_series(chart_type: str, name: str, values: List[float]) -> Dict[str, Any]:
    series: Dict[str, Any] = {"name": name, "data": values}
    if chart_type in ("bar", "horizontal_bar", "grouped_bar", "stacked_bar"):
        series["type"] = "bar"
    elif chart_type in ("line", "multi_line", "area"):
        series["type"] = "line"
    return series


def _get_value(row: Dict[str, str], key: str) -> str:
    return row.get(key, row.get(key.replace("_", ""), ""))


def _parse_num(value: object) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).replace(",", "").replace("%", ""))
    except (ValueError, AttributeError):
        return 0.0


def _empty_option(chart_type: str, msg: str) -> Dict[str, Any]:
    return {
        "title": {"text": msg, "left": "center"},
        "xAxis": {"type": "category", "data": []},
        "yAxis": {"type": "value"},
        "series": [{"type": chart_type, "data": []}],
    }


def _infer_fields_from_rows(data: List[Dict[str, str]]) -> tuple[str, List[str]]:
    if not data:
        return "", []
    first_row = data[0]
    keys = list(first_row.keys())
    if not keys:
        return "", []
    dimension = keys[0]
    metrics = [key for key in keys if key != dimension]
    return dimension, metrics


def _pivot_rows(
    data: List[Dict[str, str]],
    x_field: str,
    series_field: str,
    metric_field: str,
) -> Dict[str, Any]:
    categories: List[str] = []
    category_set = set()
    series_names: List[str] = []
    series_set = set()
    bucket: Dict[tuple[str, str], float] = {}
    for row in data:
        x = _get_value(row, x_field)
        s = _get_value(row, series_field)
        if x not in category_set:
            category_set.add(x)
            categories.append(x)
        if s not in series_set:
            series_set.add(s)
            series_names.append(s)
        bucket[(x, s)] = _parse_num(_get_value(row, metric_field))
    return {
        "categories": categories,
        "series": [
            (name, [bucket.get((category, name), 0.0) for category in categories])
            for name in series_names
        ],
    }


def _heatmap_matrix(
    data: List[Dict[str, str]],
    x_field: str,
    y_field: str,
    metric_field: str,
) -> Dict[str, Any]:
    x_values: List[str] = []
    y_values: List[str] = []
    x_set = set()
    y_set = set()
    bucket: Dict[tuple[str, str], float] = {}
    for row in data:
        x = _get_value(row, x_field)
        y = _get_value(row, y_field)
        if x not in x_set:
            x_set.add(x)
            x_values.append(x)
        if y not in y_set:
            y_set.add(y)
            y_values.append(y)
        bucket[(x, y)] = _parse_num(_get_value(row, metric_field))
    points = []
    values = []
    for xi, x in enumerate(x_values):
        for yi, y in enumerate(y_values):
            val = bucket.get((x, y), 0.0)
            values.append(val)
            points.append([xi, yi, val])
    return {
        "x": x_values,
        "y": y_values,
        "data": points,
        "min": min(values) if values else 0,
        "max": max(values) if values else 0,
    }
