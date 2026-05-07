"""Aggregate SELECT-only metrics for the BI dashboard."""

from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List

from backend.business_db import business_fetch_all, business_fetch_one, safe_table_count

logger = logging.getLogger(__name__)

_SEMANTIC_TABLES = (
    "data_source_config",
    "field_dictionary",
    "metric_definition",
    "dimension_definition",
    "alias_mapping",
    "business_term",
)


def _json_num(v: Any) -> Any:
    if isinstance(v, Decimal):
        return float(v)
    return v


def _json_date(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    return str(v)


def build_dashboard_overview() -> Dict[str, Any]:
    warnings: List[str] = []
    kpis: Dict[str, Any] = {
        "total_sales": 0.0,
        "row_count": 0,
        "min_date": None,
        "max_date": None,
        "region_count": 0,
    }
    sales_by_region: List[Dict[str, Any]] = []
    sales_by_month: List[Dict[str, Any]] = []
    customer_by_region: List[Dict[str, Any]] = []
    semantic_counts: Dict[str, int] = {}

    try:
        row = business_fetch_one(
            "SELECT COALESCE(SUM(sales_amount), 0) AS total_sales, COUNT(*) AS row_count, "
            "MIN(order_date) AS min_date, MAX(order_date) AS max_date, "
            "COUNT(DISTINCT region) AS region_count FROM sales_order"
        )
        if row:
            kpis = {
                "total_sales": float(_json_num(row.get("total_sales")) or 0),
                "row_count": int(row.get("row_count") or 0),
                "min_date": _json_date(row.get("min_date")),
                "max_date": _json_date(row.get("max_date")),
                "region_count": int(row.get("region_count") or 0),
            }
    except Exception as exc:
        logger.warning("dashboard sales_order kpis: %s", exc)
        warnings.append("无法读取 sales_order 汇总，请确认业务库中存在该表。")

    try:
        raw = business_fetch_all(
            "SELECT region, SUM(sales_amount) AS sales_amount FROM sales_order "
            "GROUP BY region ORDER BY sales_amount DESC"
        )
        sales_by_region = [
            {
                "region": str(r["region"]),
                "sales_amount": float(_json_num(r["sales_amount"]) or 0),
            }
            for r in raw
        ]
    except Exception as exc:
        logger.warning("dashboard sales_by_region: %s", exc)
        warnings.append("无法读取按区域销售额分布。")

    try:
        raw = business_fetch_all(
            "SELECT DATE_FORMAT(order_date, '%%Y-%%m') AS month, "
            "SUM(sales_amount) AS sales_amount FROM sales_order "
            "GROUP BY DATE_FORMAT(order_date, '%%Y-%%m') ORDER BY month"
        )
        sales_by_month = [
            {
                "month": str(r["month"]),
                "sales_amount": float(_json_num(r["sales_amount"]) or 0),
            }
            for r in raw
        ]
    except Exception as exc:
        logger.warning("dashboard sales_by_month: %s", exc)
        warnings.append("无法读取按月份销售额趋势。")

    try:
        raw = business_fetch_all(
            "SELECT region, SUM(active_customers) AS active_customers FROM customer_profile "
            "GROUP BY region ORDER BY region"
        )
        customer_by_region = [
            {
                "region": str(r["region"]),
                "active_customers": int(r.get("active_customers") or 0),
            }
            for r in raw
        ]
    except Exception as exc:
        logger.warning("dashboard customer_by_region: %s", exc)
        warnings.append("无法读取 customer_profile 客户活跃度。")

    for name in _SEMANTIC_TABLES:
        semantic_counts[name] = safe_table_count(name)

    return {
        "kpis": kpis,
        "sales_by_region": sales_by_region,
        "sales_by_month": sales_by_month,
        "customer_by_region": customer_by_region,
        "semantic_counts": semantic_counts,
        "warnings": warnings,
    }
