from __future__ import annotations

from typing import Dict, List

from _shared.db import MysqlCli, quote_ident

from .models import Dimension, Metric


def load_metrics(db: MysqlCli) -> Dict[str, Metric]:
    rows = db.query(
        "SELECT metric_name, metric_code, source_table, formula, business_caliber "
        "FROM metric_definition"
    )
    metrics: Dict[str, Metric] = {}
    for row in rows:
        metric = Metric(
            name=row["metric_name"],
            code=row["metric_code"],
            table=row["source_table"],
            formula=row["formula"],
            caliber=row["business_caliber"],
        )
        metrics[metric.name] = metric
        metrics[metric.code] = metric
    return metrics


def load_aliases(db: MysqlCli) -> Dict[str, str]:
    rows = db.query("SELECT alias_name, standard_name FROM alias_mapping")
    return {row["alias_name"]: row["standard_name"] for row in rows}


def load_dimensions(db: MysqlCli) -> Dict[str, List[Dimension]]:
    rows = db.query("SELECT dimension_name, field_name, source_table FROM dimension_definition")
    dimensions: Dict[str, List[Dimension]] = {}
    for row in rows:
        dim = Dimension(
            name=row["dimension_name"],
            field=row["field_name"],
            table=row["source_table"],
            expression=quote_ident(row["field_name"]),
        )
        dimensions.setdefault(dim.name, []).append(dim)

    built_ins = [
        Dimension(
            "月份",
            "stat_month",
            "customer_profile",
            "DATE_FORMAT(`stat_month`, '%Y-%m')",
        ),
        Dimension("区域", "region", "customer_profile", "`region`"),
        Dimension("客户类型", "customer_type", "customer_profile", "`customer_type`"),
        Dimension("月份", "order_date", "sales_order", "DATE_FORMAT(`order_date`, '%Y-%m')"),
    ]
    for dim in built_ins:
        dimensions.setdefault(dim.name, []).append(dim)
    return dimensions
