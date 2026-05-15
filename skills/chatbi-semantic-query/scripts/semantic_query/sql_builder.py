from __future__ import annotations

import re
from collections import OrderedDict

from _shared.db import quote_ident

from .models import FilterCondition, SemanticPlan

_EQ_PATTERN = re.compile(r"^`([^`]+)`\s*=\s*(.+)$", re.DOTALL)


def merge_equality_filters(filters: list[FilterCondition]) -> list[str]:
    """Combine multiple ``col = v`` on the same column into ``col IN (...)``."""
    by_field: OrderedDict[str, list[tuple[str, str]]] = OrderedDict()
    passthrough: list[str] = []

    for _dim_name, _value, condition in filters:
        stripped = condition.strip()
        m = _EQ_PATTERN.match(stripped)
        if not m:
            passthrough.append(condition)
            continue
        field = m.group(1)
        rhs = m.group(2).strip()
        by_field.setdefault(field, []).append((rhs, condition))

    parts: list[str] = []
    for field, items in by_field.items():
        seen: set[str] = set()
        ordered_rhs: list[str] = []
        for rhs, _ in items:
            if rhs not in seen:
                seen.add(rhs)
                ordered_rhs.append(rhs)
        if len(ordered_rhs) == 1:
            parts.append(items[0][1])
        else:
            parts.append(f"{quote_ident(field)} IN ({', '.join(ordered_rhs)})")
    return parts + passthrough


def build_sql(plan: SemanticPlan) -> str:
    metric_alias = plan.metric.name
    select_parts = [f"{plan.metric.formula} AS {quote_ident(metric_alias)}"]
    group_parts = []

    for dim in plan.dimensions:
        select_parts.insert(0, f"{dim.expression} AS {quote_ident(dim.name)}")
        group_parts.append(dim.expression)

    where_parts = merge_equality_filters(plan.filters)
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
