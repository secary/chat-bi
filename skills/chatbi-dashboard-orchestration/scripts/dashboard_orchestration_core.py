from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

CURRENT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CURRENT_DIR.parents[1]))
sys.path.insert(0, str(CURRENT_DIR.parents[2]))
sys.path.insert(0, str(CURRENT_DIR.parents[1] / "chatbi-auto-analysis" / "scripts"))
sys.path.insert(0, str(CURRENT_DIR.parents[1] / "chatbi-chart-recommendation" / "scripts"))

from _shared.output import kpi, skill_response  # noqa: E402
from display_names import domain_display_name, field_display_name  # noqa: E402
from chart_recommendation_core import recommend_chart  # noqa: E402


def orchestrate_from_input(raw: str) -> Dict[str, Any]:
    question, payload = parse_input(raw)
    return build_dashboard_package(question, payload)


def parse_input(raw: str) -> Tuple[str, Dict[str, Any]]:
    text = (raw or "").strip()
    if not text:
        return "", {}
    payload = _extract_payload(text)
    if payload is None:
        return text, {}
    if isinstance(payload, dict):
        question = str(payload.get("question") or payload.get("query") or "")
        return question, payload
    return text, {}


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


def build_dashboard_package(question: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    auto_analysis = payload.get("auto_analysis")
    if isinstance(auto_analysis, dict):
        return build_auto_analysis_dashboard(question, auto_analysis)

    overview = normalize_overview(payload)
    if not overview:
        chart_assets: List[Dict[str, Any]] = []
        kpis = build_dashboard_kpis({}, chart_assets)
        tables = build_overview_tables([], chart_assets)
        dashboard_spec = build_dashboard_spec(question, {}, kpis, chart_assets, tables)
        # 无数据时仍返回完整布局框架，并给出结构化的下一步指引
        return skill_response(
            kind="dashboard_orchestration",
            text=f"已基于「{question}」生成看板布局框架。缺少数据，暂时展示空白卡片布局，数据就绪后可自动填充。",
            data={
                "dashboard_spec": {
                    **dashboard_spec,
                    "status": "need_clarification",
                    "dashboard_intent": "overview",
                    "dashboard_title": build_title(question),
                    "confidence": 0.5,
                    "missing_inputs": [
                        "kpis",
                        "sales_by_region",
                        "sales_by_month",
                        "customer_by_region",
                    ],
                    "suggested_skill": "chatbi-semantic-query",
                    "suggested_action": "获取数据后重新调用编排，或直接查询数据后由系统自动生成看板",
                }
            },
            charts=[],
            kpis=[],
        )

    chart_assets = build_overview_chart_assets(question, overview["datasets"])
    kpis = build_dashboard_kpis(overview, chart_assets)
    tables = build_overview_tables(overview["datasets"], chart_assets)
    dashboard_spec = build_dashboard_spec(question, overview, kpis, chart_assets, tables)
    return skill_response(
        kind="dashboard_orchestration",
        text=f"已生成「{dashboard_spec['dashboard_title']}」的看板编排建议。",
        data={"dashboard_spec": dashboard_spec, "overview": overview},
        charts=[asset["option"] for asset in chart_assets],
        kpis=kpis,
    )


def build_auto_analysis_dashboard(question: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    metrics = [item for item in payload.get("metrics", []) or [] if isinstance(item, dict)]
    charts = [item for item in payload.get("charts", []) or [] if isinstance(item, dict)]
    profile = payload.get("profile") if isinstance(payload.get("profile"), dict) else {}
    kpi_values = _compute_kpi_values(metrics)
    table_rows, table_columns = _build_table_data(metrics)
    widgets = [
        {
            "id": str(item.get("id") or f"metric_{idx + 1}"),
            "title": str(item.get("name") or f"指标 {idx + 1}"),
            "type": "chart",
            "chart_index": idx,
        }
        for idx, item in enumerate(metrics)
    ]
    dashboard = {
        "markdown": f"## 上传文件看板已生成\n\n已基于 `{len(metrics)}` 个采纳指标生成图表和看板结构。",
        "title": build_title(question or "上传文件自动分析"),
        "dataset": {
            "row_count": profile.get("row_count", 0),
            "domain_guess": profile.get("domain_guess", "generic_table"),
            "domain_label": str(
                profile.get("domain_label")
                or domain_display_name(str(profile.get("domain_guess") or ""))
            ),
        },
        "widgets": widgets,
        "charts": charts,
        "metrics": metrics,
        "kpi_values": kpi_values,
        "table_rows": table_rows,
        "table_columns": table_columns,
    }
    dashboard_spec = build_generic_dashboard_spec(
        question=question,
        title=dashboard["title"],
        intent=infer_auto_analysis_intent(metrics, charts),
        kpis=kpi_values,
        chart_titles=[widget["title"] for widget in widgets],
        table_columns=table_columns,
    )
    return skill_response(
        kind="dashboard_orchestration",
        text=dashboard["markdown"],
        data={"dashboard_spec": dashboard_spec, "dashboard_middleware": dashboard},
        charts=charts,
    )


def normalize_overview(payload: Dict[str, Any]) -> Dict[str, Any]:
    source = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    if not isinstance(source, dict):
        return {}
    datasets = []
    for key, value in source.items():
        if key in {"question", "query", "warnings", "data", "auto_analysis"}:
            continue
        if isinstance(value, list) and value and all(isinstance(item, dict) for item in value):
            datasets.append(
                {
                    "key": key,
                    "title": dataset_title(key),
                    "rows": [dict(item) for item in value if isinstance(item, dict)],
                }
            )
    kpi_source = source.get("kpis") if isinstance(source.get("kpis"), dict) else None
    if kpi_source is None:
        scalar_top = {
            key: value
            for key, value in source.items()
            if key not in {"warnings", "question", "query"} and not isinstance(value, (dict, list))
        }
        kpi_source = scalar_top if scalar_top else {}
    warnings = (
        [str(item) for item in source.get("warnings", []) if item]
        if isinstance(source.get("warnings"), list)
        else []
    )
    if not datasets and not kpi_source:
        return {}
    return {
        "kpis": dict(kpi_source),
        "datasets": datasets,
        "warnings": warnings,
        "source": source,
    }


def build_overview_chart_assets(
    question: str, datasets: Sequence[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    assets: List[Dict[str, Any]] = []
    for dataset in datasets:
        rows = dataset.get("rows") or []
        if not rows:
            continue
        title = str(dataset.get("title") or "图表")
        payload = recommend_chart(f"{question} {title}".strip(), rows)
        recommendation = payload.get("data", {}).get("recommendation", {})
        charts = payload.get("charts") or []
        chart_type = str(recommendation.get("recommended_chart") or "")
        if charts and chart_type and chart_type != "kpi_card":
            assets.append(
                {
                    "key": str(dataset.get("key") or title),
                    "title": title,
                    "option": charts[0],
                    "chart_type": chart_type,
                    "rows": rows,
                    "recommendation": recommendation,
                }
            )
    return assets


def build_overview_tables(
    datasets: Sequence[Dict[str, Any]],
    chart_assets: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    chart_keys = {str(item.get("key") or "") for item in chart_assets}
    tables = []
    for dataset in datasets:
        rows = dataset.get("rows") or []
        if not rows:
            continue
        key = str(dataset.get("key") or "")
        if key in chart_keys and len(rows[0].keys()) <= 3:
            continue
        tables.append(
            {
                "key": key,
                "title": str(dataset.get("title") or "明细数据"),
                "rows": rows,
                "columns": list(rows[0].keys()) if rows and isinstance(rows[0], dict) else [],
            }
        )
    return tables


def build_dashboard_kpis(
    overview: Dict[str, Any],
    chart_assets: Sequence[Dict[str, Any]],
) -> List[Dict[str, str]]:
    cards = []
    seen_labels = set()
    scalar_candidates = extract_scalar_kpi_candidates(overview.get("kpis", {}) or {})
    for item in scalar_candidates:
        if item["label"] in seen_labels:
            continue
        seen_labels.add(item["label"])
        cards.append(kpi(item["label"], item["value"], item["unit"], item["status"]))
        if len(cards) >= 5:
            return cards

    for asset in chart_assets:
        summary = summarize_chart_asset(asset)
        if not summary:
            continue
        if summary["label"] in seen_labels:
            continue
        seen_labels.add(summary["label"])
        cards.append(kpi(summary["label"], summary["value"], summary["unit"], "neutral"))
        if len(cards) >= 5:
            break
    return cards


def extract_scalar_kpi_candidates(kpis_source: Dict[str, Any]) -> List[Dict[str, str]]:
    candidates: List[Dict[str, str]] = []
    seen_date_parts = set()
    for key, value in kpis_source.items():
        if value in (None, "", []):
            continue
        text = str(key)
        if text.endswith("_count") and _is_numeric_scalar(value):
            candidates.append(
                {
                    "label": field_display_name(text),
                    "value": format_numeric_kpi(float(value)),
                    "unit": "个",
                    "status": "neutral",
                }
            )
            continue
        if any(
            token in text.lower() for token in ["amount", "sales", "revenue", "profit", "balance"]
        ):
            if _is_numeric_scalar(value):
                candidates.append(
                    {
                        "label": field_display_name(text),
                        "value": format_numeric_kpi(float(value)),
                        "unit": "元",
                        "status": "success",
                    }
                )
            continue
        if (
            any(token in text.lower() for token in ["rate", "ratio", "pct"])
            or "率" in text
            or "占比" in text
        ):
            if _is_numeric_scalar(value):
                pct = float(value)
                candidates.append(
                    {
                        "label": field_display_name(text),
                        "value": f"{pct:.2f}".rstrip("0").rstrip("."),
                        "unit": "%",
                        "status": "neutral",
                    }
                )
            continue
        if any(token in text.lower() for token in ["avg", "average", "mean", "days", "day"]):
            if _is_numeric_scalar(value):
                candidates.append(
                    {
                        "label": field_display_name(text),
                        "value": format_numeric_kpi(float(value)),
                        "unit": "天" if "day" in text.lower() or "days" in text.lower() else "",
                        "status": "neutral",
                    }
                )
            continue
        if text.startswith("min_") or text.startswith("max_"):
            base = text[4:]
            if base in seen_date_parts:
                continue
            paired = _paired_date_range_label(base, kpis_source)
            if paired:
                seen_date_parts.add(base)
                candidates.append(paired)
            continue
        if _is_numeric_scalar(value):
            candidates.append(
                {
                    "label": field_display_name(text),
                    "value": format_numeric_kpi(float(value)),
                    "unit": "",
                    "status": "neutral",
                }
            )
    return candidates


def summarize_chart_asset(asset: Dict[str, Any]) -> Optional[Dict[str, str]]:
    rows = asset.get("rows") or []
    if not rows or not isinstance(rows[0], dict):
        return None
    first = rows[0]
    keys = list(first.keys())
    if len(keys) < 2:
        return None
    numeric_cols = [
        key
        for key in keys
        if all(_is_numeric_scalar(row.get(key)) for row in rows[: min(20, len(rows))])
    ]
    if not numeric_cols:
        return None
    metric = numeric_cols[0]
    values = [float(row.get(metric) or 0) for row in rows if _is_numeric_scalar(row.get(metric))]
    if not values:
        return None
    chart_type = str(asset.get("chart_type") or "")
    if chart_type in {"line", "multi_line", "area"}:
        value = values[-1]
        label = f"最新{field_display_name(metric)}"
    elif chart_type in {"pie", "stacked_bar", "grouped_bar", "bar", "horizontal_bar", "heatmap"}:
        value = sum(values)
        label = field_display_name(metric)
    elif chart_type == "funnel":
        value = values[0]
        label = field_display_name(metric)
    else:
        value = values[-1]
        label = field_display_name(metric)
    return {"label": label, "value": format_numeric_kpi(value), "unit": infer_unit(metric)}


def build_dashboard_spec(
    question: str,
    overview: Dict[str, Any],
    kpis: Sequence[Dict[str, str]],
    chart_assets: Sequence[Dict[str, Any]],
    tables: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    return build_generic_dashboard_spec(
        question=question,
        title=build_title(question),
        intent=infer_dashboard_intent(chart_assets, tables),
        kpis=kpis,
        chart_titles=[asset["title"] for asset in chart_assets],
        table_columns=tables[0]["columns"] if tables else [],
        warnings=overview.get("warnings", []) or [],
        filters=infer_global_filters(overview.get("datasets", []) or []),
    )


def build_generic_dashboard_spec(
    question: str,
    title: str,
    intent: str,
    kpis: Sequence[Dict[str, str]],
    chart_titles: Sequence[str],
    table_columns: Sequence[str],
    warnings: Optional[Sequence[str]] = None,
    filters: Optional[Sequence[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    sections = []
    widgets = []
    current_y = 0
    if kpis:
        sections.append({"id": "summary", "title": "关键指标", "order": len(sections) + 1})
        card_width = 12 if len(kpis) == 1 else 6 if len(kpis) == 2 else 4 if len(kpis) == 3 else 3
        for idx, card in enumerate(kpis[:6]):
            widgets.append(
                widget(
                    f"kpi_{idx + 1}",
                    "kpi",
                    card["label"],
                    "summary",
                    (idx % max(1, 12 // card_width)) * card_width,
                    current_y,
                    card_width,
                    2,
                    f"kpi_{idx + 1}",
                )
            )
        current_y += 2
    if chart_titles:
        sections.append({"id": "charts", "title": "图表分析", "order": len(sections) + 1})
        for idx, title_text in enumerate(chart_titles):
            widgets.append(
                widget(
                    f"chart_{idx + 1}",
                    "chart",
                    title_text,
                    "charts",
                    (idx % 2) * 6,
                    current_y + (idx // 2) * 4,
                    6,
                    4,
                    f"chart_{idx}",
                )
            )
        current_y += ((len(chart_titles) + 1) // 2) * 4
    if table_columns:
        sections.append({"id": "detail", "title": "明细数据", "order": len(sections) + 1})
        widgets.append(
            widget("detail_table", "table", "明细数据", "detail", 0, current_y, 12, 4, "table_0")
        )

    return {
        "status": "ready",
        "original_query": question,
        "dashboard_intent": intent,
        "dashboard_title": title,
        "confidence": 0.86,
        "layout": {"grid_columns": 12, "row_height": 80, "density": "comfortable"},
        "global_filters": list(filters or []),
        "sections": sections,
        "widgets": widgets,
        "interactions": [],
        "responsive": {
            "desktop": {"columns": 12},
            "tablet": {"columns": 12},
            "mobile": {"columns": 1},
        },
        "data_dependencies": [],
        "decision_factors": [
            f"kpi_cards={len(kpis)}",
            f"charts={len(chart_titles)}",
            f"detail_columns={len(table_columns)}",
        ],
        "warnings": list(warnings or []),
        "missing_inputs": [],
    }


def widget(
    widget_id: str,
    widget_type: str,
    title: str,
    section_id: str,
    x: int,
    y: int,
    w: int,
    h: int,
    data_ref: str,
) -> Dict[str, Any]:
    return {
        "id": widget_id,
        "type": widget_type,
        "chart_type": "table" if widget_type == "table" else widget_type,
        "title": title,
        "section_id": section_id,
        "priority": 1,
        "position": {"x": x, "y": y, "w": w, "h": h},
        "chart_spec_ref": None,
        "chart_spec": {},
        "data_ref": data_ref,
        "visible": True,
    }


def infer_dashboard_intent(
    chart_assets: Sequence[Dict[str, Any]],
    tables: Sequence[Dict[str, Any]],
) -> str:
    chart_types = {str(item.get("chart_type") or "") for item in chart_assets}
    if "funnel" in chart_types:
        return "funnel_analysis"
    if "heatmap" in chart_types:
        return "matrix_analysis"
    if chart_types & {"line", "multi_line", "area"}:
        return "trend_analysis"
    if chart_types & {"pie", "stacked_bar", "grouped_bar", "horizontal_bar", "bar"}:
        return "comparison_analysis"
    if tables:
        return "detail_overview"
    return "overview"


def infer_auto_analysis_intent(
    metrics: Sequence[Dict[str, Any]],
    charts: Sequence[Dict[str, Any]],
) -> str:
    if any(_chart_series_type(chart) == "funnel" for chart in charts):
        return "funnel_analysis"
    if any(_chart_series_type(chart) == "heatmap" for chart in charts):
        return "matrix_analysis"
    if any(str(item.get("chart_hint") or "") in {"line", "multi_line", "area"} for item in metrics):
        return "trend_analysis"
    return "uploaded_file_auto_analysis"


def _chart_series_type(chart: Dict[str, Any]) -> str:
    series = chart.get("series")
    if isinstance(series, list) and series and isinstance(series[0], dict):
        return str(series[0].get("type") or "")
    return ""


def build_title(question: str) -> str:
    text = (question or "").strip()
    if not text:
        return "分析看板"
    if text.endswith("看板") or text.endswith("仪表盘"):
        return text
    return f"{text}看板"


def infer_global_filters(datasets: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    discovered: Dict[str, Dict[str, Any]] = {}
    for dataset in datasets:
        rows = dataset.get("rows") or []
        if not rows or not isinstance(rows[0], dict):
            continue
        for field in rows[0].keys():
            key = str(field)
            normalized = key.lower()
            if key in discovered:
                continue
            if (
                any(token in normalized for token in ["date", "month", "time", "year"])
                or "日期" in key
                or "月份" in key
            ):
                discovered[key] = {
                    "field": key,
                    "label": field_display_name(key),
                    "type": "date_range",
                    "required": False,
                }
            elif any(
                token in normalized for token in ["region", "branch", "channel", "type", "category"]
            ) or any(token in key for token in ["区域", "支行", "渠道", "类型", "类别"]):
                discovered[key] = {
                    "field": key,
                    "label": field_display_name(key),
                    "type": "select",
                    "required": False,
                }
    return list(discovered.values())[:4]


def dataset_title(key: str) -> str:
    text = str(key or "").strip()
    if not text:
        return "数据集"
    return field_display_name(text)


def infer_unit(metric: str) -> str:
    text = str(metric or "").lower()
    if (
        any(token in text for token in ["rate", "ratio", "pct"])
        or "率" in metric
        or "占比" in metric
    ):
        return "%"
    if any(
        token in text for token in ["amount", "sales", "revenue", "profit", "balance", "deal_size"]
    ):
        return "元"
    if any(token in text for token in ["day", "days"]) or "天" in metric:
        return "天"
    return ""


def format_numeric_kpi(value: float) -> str:
    abs_value = abs(value)
    if abs_value >= 1e8:
        return f"{value / 1e8:.1f}亿"
    if abs_value >= 1e4:
        return f"{value / 1e4:.1f}万"
    return str(int(value)) if value == int(value) else f"{value:.2f}"


def _is_numeric_scalar(value: Any) -> bool:
    if isinstance(value, (int, float)):
        return True
    if value is None:
        return False
    try:
        float(str(value).replace(",", "").replace("%", "").strip())
        return True
    except (TypeError, ValueError):
        return False


def _paired_date_range_label(base: str, kpis_source: Dict[str, Any]) -> Optional[Dict[str, str]]:
    start = kpis_source.get(f"min_{base}")
    end = kpis_source.get(f"max_{base}")
    if start in (None, "") or end in (None, ""):
        return None
    return {
        "label": f"{field_display_name(base)}范围",
        "value": f"{start} ~ {end}",
        "unit": "",
        "status": "neutral",
    }


def _compute_kpi_values(metrics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    result = []
    seen_signatures = set()
    for item in metrics:
        rows = item.get("rows") or []
        formula = item.get("formula") if isinstance(item.get("formula"), dict) else {}
        signature = json.dumps(formula, ensure_ascii=False, sort_keys=True)
        if not rows or signature in seen_signatures:
            continue
        seen_signatures.add(signature)
        metric_name = str(item.get("name") or item.get("id") or "指标")
        values = _extract_metric_values(rows, metric_name)
        if not values:
            continue
        op = str(formula.get("op") or "").lower()
        if op in {"divide", "ratio", "ratio_percent"}:
            value = sum(values) / len(values)
        else:
            value = sum(values)
        result.append(
            {
                "label": metric_name,
                "value": format_numeric_kpi(value),
                "unit": infer_unit(metric_name),
                "status": "success" if op in {"sum", "count", "count_distinct"} else "neutral",
            }
        )
        if len(result) >= 6:
            break
    return result


def _extract_metric_values(rows: Sequence[Dict[str, Any]], metric_name: str) -> List[float]:
    values = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if metric_name in row and _is_numeric_scalar(row.get(metric_name)):
            values.append(float(row.get(metric_name)))
    return values


def _build_table_data(
    metrics: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[str]]:
    if not metrics:
        return [], []
    primary = max(metrics, key=lambda m: len(m.get("rows") or []))
    rows = primary.get("rows") or []
    if not rows or not isinstance(rows[0], dict):
        return [], []
    columns = list(rows[0].keys())
    return [{col: str(row.get(col, "")) for col in columns} for row in rows[:30]], columns
