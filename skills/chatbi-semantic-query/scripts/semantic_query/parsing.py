'''Extract natural language query components into structured information.'''
from __future__ import annotations

import os
import re
from typing import Dict, Iterable, List, Optional

from _shared.db import MysqlCli, quote_ident, quote_literal

from .models import Dimension, FilterCondition, Metric, TimeFilter

DEFAULT_YEAR = int(os.getenv("CHATBI_DEFAULT_YEAR", "2026"))

# Prefer alias_mapping for business-specific dimension synonyms.
# Keep only generic language fallbacks here so the semantic layer remains
# data-driven and most new wording can be added without code changes.
FALLBACK_DIMENSION_SYNONYMS = {
    "月份": ["时间", "按月", "趋势", "发生时间", "统计时间"],
    "区域": ["各区域", "区域对比", "所属区域"],
    "部门": ["负责部门", "销售部门"],
    "产品类别": ["服务类别"],
    "产品名称": ["产品", "具体服务"],
    "渠道": ["来源渠道"],
    "客户类型": ["客户群体"],
}


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", text).lower()


def pick_metric(question: str, metrics: Dict[str, Metric], aliases: Dict[str, str]) -> Metric:
    normalized = normalize_text(question)
    candidates = []
    for alias, standard in aliases.items():
        if normalize_text(alias) in normalized and standard in metrics:
            candidates.append((len(alias), metrics[standard]))
    for name, metric in metrics.items():
        if normalize_text(name) in normalized:
            candidates.append((len(name), metric))
    if candidates:
        return sorted(candidates, key=lambda item: item[0], reverse=True)[0][1]
    return metrics["销售额"]


def dimension_for_table(
    name: str, table: str, dimensions: Dict[str, List[Dimension]]
) -> Optional[Dimension]:
    for dim in dimensions.get(name, []):
        if dim.table == table:
            return dim
    return None


def build_dimension_synonyms(
    dimensions: Dict[str, List[Dimension]], aliases: Dict[str, str]
) -> Dict[str, List[str]]:
    synonyms = {
        name: [name] for name in dimensions if not (name == "时间" and "月份" in dimensions)
    }
    for name, words in FALLBACK_DIMENSION_SYNONYMS.items():
        if name in dimensions:
            synonyms.setdefault(name, [])
            synonyms[name].extend(words)

    for alias, standard in aliases.items():
        if standard == "时间" and "月份" in dimensions:
            standard = "月份"
        if standard in dimensions:
            synonyms.setdefault(standard, [])
            synonyms[standard].append(alias)

    return {name: sorted(set(words), key=len, reverse=True) for name, words in synonyms.items()}


def pick_dimensions(
    question: str,
    metric: Metric,
    dimensions: Dict[str, List[Dimension]],
    aliases: Dict[str, str],
) -> List[Dimension]:
    normalized = normalize_text(question)
    wanted: List[Dimension] = []

    for name, words in build_dimension_synonyms(dimensions, aliases).items():
        if any(normalize_text(word) in normalized for word in words):
            dim = dimension_for_table(name, metric.table, dimensions)
            if dim and dim not in wanted:
                wanted.append(dim)

    if not wanted and any(word in question for word in ["排行", "排名", "对比", "最高", "最低"]):
        dim = dimension_for_table("区域", metric.table, dimensions)
        if dim:
            wanted.append(dim)

    return wanted


def load_distinct_values(
    db: MysqlCli, table: str, dimensions: Iterable[Dimension]
) -> Dict[str, List[str]]:
    values: Dict[str, List[str]] = {}
    for dim in dimensions:
        if dim.table != table or dim.field in values:
            continue
        sql = (
            f"SELECT DISTINCT {quote_ident(dim.field)} AS value "
            f"FROM {quote_ident(table)} ORDER BY {quote_ident(dim.field)}"
        )
        values[dim.field] = [row["value"] for row in db.query(sql)]
    return values


def parse_filters(
    question: str,
    metric: Metric,
    dimensions: Dict[str, List[Dimension]],
    db: MysqlCli,
) -> List[FilterCondition]:
    all_table_dims = [
        dim for dim_list in dimensions.values() for dim in dim_list if dim.table == metric.table
    ]
    distinct_values = load_distinct_values(db, metric.table, all_table_dims)
    dimension_names = set(dimensions.keys())
    filters: List[FilterCondition] = []
    for dim in all_table_dims:
        for value in distinct_values.get(dim.field, []):
            if value in dimension_names:
                continue
            if value and value in question:
                condition = f"{quote_ident(dim.field)} = {quote_literal(value)}"
                item = (dim.name, value, condition)
                if item not in filters:
                    filters.append(item)
    return filters


def month_bounds(year: int, start_month: int, end_month: int) -> tuple[str, str]:
    end = f"{year + 1}-01-01" if end_month == 12 else f"{year}-{end_month + 1:02d}-01"
    return f"{year}-{start_month:02d}-01", end


def default_year_for_table(db: MysqlCli, table: str) -> int:
    date_field = "order_date" if table == "sales_order" else "stat_month"
    sql = (
        f"SELECT MAX(YEAR({quote_ident(date_field)})) AS default_year " f"FROM {quote_ident(table)}"
    )
    rows = db.query(sql)
    if rows and rows[0].get("default_year"):
        return int(rows[0]["default_year"])
    return DEFAULT_YEAR


def parse_time_filter(
    question: str, table: str, default_year: int = DEFAULT_YEAR
) -> Optional[TimeFilter]:
    date_field = "order_date" if table == "sales_order" else "stat_month"
    patterns = [
        (
            r"(20\d{2})\s*年\s*(\d{1,2})\s*月?\s*(?:-|到|至|~)\s*(\d{1,2})\s*月",
            lambda year, start, end: month_bounds(year, start, end),
        ),
        (
            r"(20\d{2})\s*年\s*(\d{1,2})\s*月",
            lambda year, month: month_bounds(year, month, month),
        ),
        (
            r"(?<!年)(\d{1,2})\s*月?\s*(?:-|到|至|~)\s*(\d{1,2})\s*月",
            lambda start, end: month_bounds(default_year, start, end),
        ),
        (
            r"(?<!年)(\d{1,2})\s*月",
            lambda month: month_bounds(default_year, month, month),
        ),
    ]
    for pattern, builder in patterns:
        match = re.search(pattern, question)
        if not match:
            continue
        bounds = builder(*map(int, match.groups()))
        start, end = bounds
        return (
            date_field,
            f"{quote_ident(date_field)} >= {quote_literal(start)} AND "
            f"{quote_ident(date_field)} < {quote_literal(end)}",
        )

    match = re.search(r"(20\d{2})\s*年", question)
    if match:
        year = int(match.group(1))
        return (
            date_field,
            f"{quote_ident(date_field)} >= {quote_literal(str(year) + '-01-01')} AND "
            f"{quote_ident(date_field)} < {quote_literal(str(year + 1) + '-01-01')}",
        )
    return None


def parse_limit(question: str) -> Optional[int]:
    match = re.search(r"(?:top|前)\s*(\d+)", question, re.IGNORECASE)
    if match:
        return max(1, min(int(match.group(1)), 100))
    if any(word in question for word in ["最高", "最低", "第一"]):
        return 1
    return None


def wants_ordering(question: str, has_dimensions: bool) -> bool:
    return has_dimensions and any(
        word in question for word in ["排行", "排名", "最高", "最低", "top", "Top", "对比"]
    )
