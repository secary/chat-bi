from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills"))
sys.path.insert(0, str(ROOT / "skills" / "chatbi-semantic-query" / "scripts"))

from semantic_query.parsing import pick_metric
from semantic_query.planner import make_plan
from semantic_query.presenters import build_json_payload


class StubDb:
    def query(self, sql: str):
        if "FROM metric_definition" in sql:
            return [
                {
                    "metric_name": "销售额",
                    "metric_code": "sales_amount",
                    "source_table": "sales_order",
                    "formula": "SUM(sales_amount)",
                    "business_caliber": "订单销售额汇总",
                },
                {
                    "metric_name": "毛利率",
                    "metric_code": "gross_profit_rate",
                    "source_table": "sales_order",
                    "formula": "SUM(gross_profit) / SUM(sales_amount)",
                    "business_caliber": "毛利占销售额比例",
                },
            ]
        if "FROM alias_mapping" in sql:
            return [{"alias_name": "收入", "standard_name": "销售额"}]
        if "FROM dimension_definition" in sql:
            return [
                {"dimension_name": "区域", "field_name": "region", "source_table": "sales_order"}
            ]
        if "MAX(YEAR(`order_date`))" in sql:
            return [{"default_year": "2026"}]
        if "SELECT DISTINCT `order_date` AS value" in sql:
            return [{"value": "2026-01-15"}, {"value": "2026-02-01"}]
        if "SELECT DISTINCT `region` AS value" in sql:
            return [{"value": "华东"}, {"value": "华南"}]
        raise AssertionError(f"Unexpected SQL: {sql}")


def test_make_plan_builds_rank_sql_from_split_modules():
    plan = make_plan("1-4月各区域收入排行", StubDb())

    assert plan.metric.name == "销售额"
    assert plan.dimensions[0].name == "区域"
    assert plan.sql == (
        "SELECT `region` AS `区域`, SUM(sales_amount) AS `销售额` "
        "FROM `sales_order` "
        "WHERE `order_date` >= '2026-01-01' AND `order_date` < '2026-05-01' "
        "GROUP BY `region` ORDER BY `销售额` DESC"
    )


def test_make_plan_prefers_db_aliases_for_dimensions():
    plan = make_plan("1-4月大区收入排行", StubDb())

    assert plan.dimensions[0].name == "区域"


def test_make_plan_keeps_generic_fallback_dimension_words():
    plan = make_plan("销售额按月趋势", StubDb())

    assert plan.dimensions[0].name == "月份"


def test_pick_metric_prefers_rate_metric_when_multiple_metrics_match():
    metrics = {
        "销售额": type("MetricObj", (), {"name": "销售额"})(),
        "毛利率": type("MetricObj", (), {"name": "毛利率"})(),
    }
    metrics["sales_amount"] = metrics["销售额"]
    metrics["gross_profit_rate"] = metrics["毛利率"]

    picked = pick_metric("2-4月销售额毛利率排行", metrics, {})

    assert picked.name == "毛利率"


def test_make_plan_uses_rate_metric_for_sales_amount_margin_ranking():
    plan = make_plan("2-4月销售额毛利率排行", StubDb())

    assert plan.metric.name == "毛利率"
    assert "SUM(gross_profit) / SUM(sales_amount)" in plan.sql


def test_build_json_payload_includes_plan_summary_when_plan_provided():
    plan = make_plan("1-4月各区域收入排行", StubDb())
    payload = build_json_payload(
        "1-4月各区域收入排行",
        plan.sql,
        [{"区域": "华东", "销售额": "100.00"}],
        plan=plan,
    )

    assert payload["data"]["plan_summary"] == {
        "metric": "销售额",
        "metric_code": "sales_amount",
        "source_table": "sales_order",
        "dimensions": ["区域"],
        "filters": [],
        "time_filter": "`order_date` >= '2026-01-01' AND `order_date` < '2026-05-01'",
        "order_by_metric_desc": True,
        "limit": None,
    }
    assert payload["data"]["plan_trace"][0] == "收到问数请求：1-4月各区域收入排行"
    assert payload["data"]["plan_trace"][-1].startswith("生成 SQL：SELECT `region` AS `区域`")


def test_build_json_payload_keeps_chart_plan_for_trend_rows():
    payload = build_json_payload(
        "2026年销售额按月趋势",
        "SELECT ...",
        [
            {"月份": "2026-01", "销售额": "100.00"},
            {"月份": "2026-02", "销售额": "120.00"},
        ],
    )

    assert payload["kind"] == "table"
    assert payload["chart_plan"]["chart_type"] == "line"
    assert payload["chart_plan"]["dimension"] == "月份"


def test_build_json_payload_builds_kpi_for_single_rate_metric():
    payload = build_json_payload(
        "华东4月毛利率",
        "SELECT ...",
        [{"毛利率": "0.369767"}],
    )

    assert payload["text"] == "查询完成：毛利率: 36.98%"
    assert payload["kpis"] == [
        {"label": "毛利率", "value": "36.98", "unit": "%", "status": "neutral"}
    ]


def test_build_json_payload_builds_kpi_for_single_row_grouped_metric():
    payload = build_json_payload(
        "线上渠道软件服务销售额是多少",
        "SELECT ...",
        [{"渠道": "线上", "销售额": "700000.00"}],
    )

    assert payload["kpis"] == [
        {"label": "销售额", "value": "700000.00", "unit": "", "status": "neutral"}
    ]
    assert "chart_plan" not in payload


def test_build_json_payload_treats_null_aggregate_as_no_data():
    payload = build_json_payload(
        "2024年销售额",
        "SELECT ...",
        [{"销售额": "NULL"}],
    )

    assert payload["text"] == "查询完成，未返回数据。"
    assert payload["kpis"] == []
