from __future__ import annotations

import re

from _shared.db import MysqlCli

from .metadata import load_aliases, load_dimensions, load_metrics
from .models import SemanticPlan
from .parsing import (
    default_year_for_table,
    dimension_for_table,
    parse_filters,
    parse_limit,
    parse_time_filter,
    pick_dimensions,
    pick_metric,
    wants_ordering,
)
from .sql_builder import build_sql

_VISUAL_WORDS = ("图表", "画图", "可视化", "趋势图", "折线图", "柱状图", "饼图", "看板")


def _has_multi_month_range(question: str) -> bool:
    return bool(
        re.search(
            r"(?:20\d{2}\s*年\s*)?\d{1,2}\s*月?\s*(?:-|到|至|~|和|与|、)\s*\d{1,2}\s*月",
            question,
        )
    )


def _should_default_month_dimension(question: str) -> bool:
    if not _has_multi_month_range(question):
        return False
    return any(
        word in question
        for word in (*_VISUAL_WORDS, "对比", "趋势", "变化", "各自", "分别", "明细")
    )


def make_plan(question: str, db: MysqlCli) -> SemanticPlan:
    metrics = load_metrics(db)
    aliases = load_aliases(db)
    dimensions = load_dimensions(db)
    metric = pick_metric(question, metrics, aliases)
    picked_dimensions = pick_dimensions(question, metric, dimensions, aliases)
    if not picked_dimensions and _should_default_month_dimension(question):
        month_dim = dimension_for_table("月份", metric.table, dimensions)
        if month_dim:
            picked_dimensions.append(month_dim)
    filters = parse_filters(question, metric, dimensions, db)
    time_filter = parse_time_filter(
        question,
        metric.table,
        default_year_for_table(db, metric.table),
    )
    plan = SemanticPlan(
        question=question,
        metric=metric,
        dimensions=picked_dimensions,
        filters=filters,
        time_filter=time_filter,
        order_by_metric_desc=wants_ordering(question, bool(picked_dimensions)),
        limit=parse_limit(question),
        sql="",
    )
    plan.sql = build_sql(plan)
    return plan
