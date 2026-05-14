from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

CURRENT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CURRENT_DIR.parents[1]))
sys.path.insert(0, str(CURRENT_DIR.parents[2]))

from _shared.output import kpi, skill_response  # noqa: E402


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
    dashboard_spec = build_dashboard_spec(question, overview)
    if not overview:
        # 无数据时仍返回完整布局框架，并给出结构化的下一步指引
        return skill_response(
            kind="dashboard_orchestration",
            text=f"已基于「{question}」生成看板布局框架。缺少数据，暂时展示空白卡片布局，数据就绪后可自动填充。",
            data={
                "dashboard_spec": {
                    **dashboard_spec,
                    "status": "need_clarification",
                    "dashboard_intent": infer_dashboard_intent(question),
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

    charts = build_dashboard_charts(overview)
    kpis = build_dashboard_kpis(overview)
    return skill_response(
        kind="dashboard_orchestration",
        text=f"已生成「{dashboard_spec['dashboard_title']}」的看板编排建议。",
        data={"dashboard_spec": dashboard_spec, "overview": overview},
        charts=charts,
        kpis=kpis,
    )


def build_auto_analysis_dashboard(question: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    metrics = [item for item in payload.get("metrics", []) or [] if isinstance(item, dict)]
    charts = [item for item in payload.get("charts", []) or [] if isinstance(item, dict)]
    profile = payload.get("profile") if isinstance(payload.get("profile"), dict) else {}
    dashboard = {
        "markdown": f"## 上传文件看板已生成\n\n已基于 `{len(metrics)}` 个采纳指标生成图表和看板结构。",
        "title": build_title(question or "上传文件自动分析"),
        "dataset": {
            "row_count": profile.get("row_count", 0),
            "domain_guess": profile.get("domain_guess", "generic_table"),
        },
        "widgets": [
            {
                "id": str(item.get("id") or f"metric_{idx + 1}"),
                "title": str(item.get("name") or f"指标 {idx + 1}"),
                "type": "chart",
                "chart_index": idx,
            }
            for idx, item in enumerate(metrics)
        ],
        "charts": charts,
        "metrics": metrics,
    }
    dashboard_spec = {
        "status": "ready",
        "original_query": question,
        "dashboard_intent": "uploaded_file_auto_analysis",
        "dashboard_title": dashboard["title"],
        "confidence": 0.82,
        "layout": {"grid_columns": 12, "row_height": 80, "density": "comfortable"},
        "sections": [
            {"id": "summary", "title": "自动分析指标", "order": 1},
            {"id": "charts", "title": "图表看板", "order": 2},
        ],
        "widgets": [
            widget(
                str(item.get("id") or f"metric_{idx + 1}"),
                "chart",
                str(item.get("name") or f"指标 {idx + 1}"),
                "charts",
                (idx % 2) * 6,
                (idx // 2) * 4,
                6,
                4,
                f"chart_{idx}",
            )
            for idx, item in enumerate(metrics)
        ],
        "warnings": [],
        "missing_inputs": [],
    }
    return skill_response(
        kind="dashboard_orchestration",
        text=dashboard["markdown"],
        data={"dashboard_spec": dashboard_spec, "dashboard_middleware": dashboard},
        charts=charts,
    )


def normalize_overview(payload: Dict[str, Any]) -> Dict[str, Any]:
    required = {"kpis", "sales_by_region", "sales_by_month", "customer_by_region"}
    if required <= payload.keys():
        return payload
    data = payload.get("data")
    if isinstance(data, dict) and required <= data.keys():
        return data
    return {}


def build_dashboard_spec(question: str, overview: Dict[str, Any]) -> Dict[str, Any]:
    kpis = overview.get("kpis", {}) or {}
    warnings: List[str] = list(overview.get("warnings", []) or [])
    if not overview.get("sales_by_month"):
        warnings.append("缺少销售趋势数据，主趋势图可能为空。")
    return {
        "status": "ready",
        "original_query": question,
        "dashboard_intent": infer_dashboard_intent(question),
        "dashboard_title": build_title(question),
        "confidence": 0.9,
        "layout": {"grid_columns": 12, "row_height": 80, "density": "comfortable"},
        "global_filters": [
            {"field": "time_range", "label": "统计期", "type": "date_range", "required": False},
            {"field": "region", "label": "区域", "type": "select", "required": False},
        ],
        "sections": [
            {"id": "summary", "title": "核心指标", "order": 1},
            {"id": "trend", "title": "趋势分析", "order": 2},
            {"id": "breakdown", "title": "结构拆解", "order": 3},
            {"id": "detail", "title": "补充视图", "order": 4},
        ],
        "widgets": [
            widget("sales_kpi", "kpi", "销售总额", "summary", 0, 0, 3, 2, "kpi_total_sales"),
            widget("row_count_kpi", "kpi", "订单明细条数", "summary", 3, 0, 3, 2, "kpi_row_count"),
            widget(
                "region_count_kpi", "kpi", "覆盖区域数", "summary", 6, 0, 3, 2, "kpi_region_count"
            ),
            widget("sales_trend", "chart", "销售额趋势", "trend", 0, 2, 7, 4, "chart_sales_trend"),
            widget(
                "region_share",
                "chart",
                "销售额占比（按区域）",
                "breakdown",
                7,
                2,
                5,
                4,
                "chart_region_share",
            ),
            widget(
                "active_customer",
                "chart",
                "活跃客户（按区域）",
                "detail",
                0,
                6,
                12,
                4,
                "chart_active_customer",
            ),
        ],
        "interactions": [
            {
                "type": "cross_filter",
                "source_widget_id": "region_share",
                "target_widget_ids": ["active_customer"],
                "join_fields": ["region"],
            }
        ],
        "responsive": {
            "desktop": {"columns": 12},
            "tablet": {"columns": 12},
            "mobile": {"columns": 1},
        },
        "data_dependencies": ["kpis", "sales_by_region", "sales_by_month", "customer_by_region"],
        "decision_factors": decision_factors(overview, kpis),
        "warnings": warnings,
        "missing_inputs": [],
    }


def build_dashboard_charts(overview: Dict[str, Any]) -> List[Dict[str, Any]]:
    from backend.renderers.chart import plan_to_option

    charts: List[Dict[str, Any]] = []
    month_rows = stringify_rows(overview.get("sales_by_month", []))
    if month_rows:
        charts.append(
            plan_to_option(
                {"chart_type": "line", "dimension": "month", "metrics": ["sales_amount"]},
                month_rows,
            )
        )
    region_rows = stringify_rows(overview.get("sales_by_region", []))
    if region_rows:
        charts.append(
            plan_to_option(
                {"chart_type": "pie", "dimension": "region", "metrics": ["sales_amount"]},
                region_rows,
            )
        )
    customer_rows = stringify_rows(overview.get("customer_by_region", []))
    if customer_rows:
        charts.append(
            plan_to_option(
                {"chart_type": "bar", "dimension": "region", "metrics": ["active_customers"]},
                customer_rows,
            )
        )
    return charts


def build_dashboard_kpis(overview: Dict[str, Any]) -> List[Dict[str, str]]:
    kpis = overview.get("kpis", {}) or {}
    return [
        kpi("销售总额", fmt_num(kpis.get("total_sales", 0)), "元", "success"),
        kpi("订单明细条数", str(kpis.get("row_count", 0)), "条", "neutral"),
        kpi("覆盖区域数", str(kpis.get("region_count", 0)), "个", "neutral"),
        kpi("数据时间范围", date_range(kpis), "", "neutral"),
    ]


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


def infer_dashboard_intent(question: str) -> str:
    text = question or ""
    if any(word in text for word in ["风险", "不良", "逾期"]):
        return "risk_analysis"
    if any(word in text for word in ["经营", "销售", "业绩"]):
        return "performance_overview"
    return "overview"


def build_title(question: str) -> str:
    text = (question or "").strip()
    if not text:
        return "经营概览看板"
    if text.endswith("看板") or text.endswith("仪表盘"):
        return text
    return f"{text}看板"


def decision_factors(overview: Dict[str, Any], kpis: Dict[str, Any]) -> List[str]:
    return [
        f"区域销售图数据量={len(overview.get('sales_by_region', []) or [])}",
        f"月度趋势数据量={len(overview.get('sales_by_month', []) or [])}",
        f"总销售额={kpis.get('total_sales', 0)}",
    ]


def stringify_rows(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, str]]:
    return [
        {key: str(value) if value is not None else "" for key, value in row.items()}
        for row in rows
        if isinstance(row, dict)
    ]


def fmt_num(value: Any) -> str:
    try:
        return str(int(float(str(value))))
    except (TypeError, ValueError):
        return "0"


def date_range(kpis: Dict[str, Any]) -> str:
    start = kpis.get("min_date")
    end = kpis.get("max_date")
    return f"{start} ~ {end}" if start and end else "—"
