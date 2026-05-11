from __future__ import annotations

from _shared.db import quote_ident

from .models import SemanticPlan


def build_sql(plan: SemanticPlan) -> str:
    metric_alias = plan.metric.name
    select_parts = [f"{plan.metric.formula} AS {quote_ident(metric_alias)}"]
    group_parts = []

    for dim in plan.dimensions:
        select_parts.insert(0, f"{dim.expression} AS {quote_ident(dim.name)}")
        group_parts.append(dim.expression)

    where_parts = [condition for _, _, condition in plan.filters]
    if plan.time_filter:
        where_parts.append(plan.time_filter[1])

    sql = f"SELECT {', '.join(select_parts)} FROM {quote_ident(plan.metric.table)}"
    if where_parts:
        sql += " WHERE " + " AND ".join(where_parts)
    if group_parts:
        sql += " GROUP BY " + ", ".join(group_parts)
    if plan.order_by_metric_desc:
        direction = "ASC" if "最低" in plan.question else "DESC"
        sql += f" ORDER BY {quote_ident(metric_alias)} {direction}"
    if plan.limit:
        sql += f" LIMIT {plan.limit}"
    return sql
