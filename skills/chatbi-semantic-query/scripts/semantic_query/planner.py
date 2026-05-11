from __future__ import annotations

from _shared.db import MysqlCli

from .metadata import load_aliases, load_dimensions, load_metrics
from .models import SemanticPlan
from .parsing import (
    default_year_for_table,
    parse_filters,
    parse_limit,
    parse_time_filter,
    pick_dimensions,
    pick_metric,
    wants_ordering,
)
from .sql_builder import build_sql


def make_plan(question: str, db: MysqlCli) -> SemanticPlan:
    metrics = load_metrics(db)
    aliases = load_aliases(db)
    dimensions = load_dimensions(db)
    metric = pick_metric(question, metrics, aliases)
    picked_dimensions = pick_dimensions(question, metric, dimensions, aliases)
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
