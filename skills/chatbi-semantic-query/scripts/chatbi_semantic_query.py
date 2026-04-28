#!/usr/bin/env python3
"""
Lightweight ChatBI semantic query script.

It maps a Chinese natural-language question to governed metric SQL using the
metadata tables in the demo MySQL database, then executes the generated query.
No Python MySQL package is required; the script uses the local `mysql` CLI.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


DEFAULT_DB = {
    "host": os.getenv("CHATBI_DB_HOST", "127.0.0.1"),
    "port": os.getenv("CHATBI_DB_PORT", "3307"),
    "user": os.getenv("CHATBI_DB_USER", "demo_user"),
    "password": os.getenv("CHATBI_DB_PASSWORD", "demo_pass"),
    "database": os.getenv("CHATBI_DB_NAME", "chatbi_demo"),
}


@dataclass(frozen=True)
class Metric:
    name: str
    code: str
    table: str
    formula: str
    caliber: str


@dataclass(frozen=True)
class Dimension:
    name: str
    field: str
    table: str
    expression: str


@dataclass
class SemanticPlan:
    question: str
    metric: Metric
    dimensions: List[Dimension]
    filters: List[Tuple[str, str, str]]
    time_filter: Optional[Tuple[str, str]]
    order_by_metric_desc: bool
    limit: Optional[int]
    sql: str


class MysqlCli:
    def __init__(self, config: Dict[str, str]):
        self.config = config
        self.mysql_cmd = os.getenv("CHATBI_MYSQL_CMD", "mysql")

    def query(self, sql: str) -> List[Dict[str, str]]:
        cmd = [
            self.mysql_cmd,
            f"-h{self.config['host']}",
            f"-P{self.config['port']}",
            f"-u{self.config['user']}",
            f"-p{self.config['password']}",
            "--batch",
            "--raw",
            "--default-character-set=utf8mb4",
            self.config["database"],
            "-e",
            sql,
        ]
        proc = subprocess.run(cmd, text=True, capture_output=True, check=False)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())
        lines = [line for line in proc.stdout.splitlines() if line.strip()]
        if not lines:
            return []
        reader = csv.DictReader(lines, delimiter="\t")
        return [dict(row) for row in reader]


def quote_ident(identifier: str) -> str:
    if not identifier or "`" in identifier or "\x00" in identifier:
        raise ValueError(f"Unsafe identifier: {identifier}")
    return f"`{identifier}`"


def quote_literal(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "''") + "'"


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", text).lower()


DIMENSION_SYNONYMS = {
    "月份": [
        "时间",
        "日期",
        "月份",
        "月度",
        "按月",
        "每月",
        "趋势",
        "时间趋势",
        "发生时间",
        "统计时间",
    ],
    "区域": [
        "区域",
        "各区域",
        "区域对比",
        "大区",
        "地区",
        "片区",
        "市场",
        "所属区域",
        "业务区域",
    ],
    "部门": [
        "部门",
        "团队",
        "组织",
        "业务部门",
        "负责部门",
        "销售部门",
    ],
    "产品类别": [
        "产品类别",
        "产品线",
        "品类",
        "业务线",
        "产品类型",
        "产品分类",
        "服务类别",
    ],
    "产品名称": [
        "产品名称",
        "产品",
        "具体产品",
        "产品名",
        "服务名称",
        "具体服务",
    ],
    "渠道": [
        "渠道",
        "来源",
        "成交来源",
        "成交渠道",
        "获客渠道",
        "销售渠道",
        "来源渠道",
        "业务来源",
    ],
    "客户类型": [
        "客户类型",
        "客户类别",
        "客户分层",
        "客户层级",
        "客群",
        "客户群",
        "客户群体",
        "客户结构",
    ],
}


def load_metrics(db: MysqlCli) -> Dict[str, Metric]:
    rows = db.query(
        "SELECT metric_name, metric_code, source_table, formula, business_caliber "
        "FROM metric_definition"
    )
    metrics = {}
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
    rows = db.query(
        "SELECT dimension_name, field_name, source_table FROM dimension_definition"
    )
    dimensions: Dict[str, List[Dimension]] = {}
    for row in rows:
        dim = Dimension(
            name=row["dimension_name"],
            field=row["field_name"],
            table=row["source_table"],
            expression=quote_ident(row["field_name"]),
        )
        dimensions.setdefault(dim.name, []).append(dim)

    # The demo metadata currently defines most dimensions for sales_order.
    # These built-ins make customer_profile metrics usable as well.
    built_ins = [
        Dimension("月份", "stat_month", "customer_profile", "DATE_FORMAT(`stat_month`, '%Y-%m')"),
        Dimension("区域", "region", "customer_profile", "`region`"),
        Dimension("客户类型", "customer_type", "customer_profile", "`customer_type`"),
        Dimension("月份", "order_date", "sales_order", "DATE_FORMAT(`order_date`, '%Y-%m')"),
    ]
    for dim in built_ins:
        dimensions.setdefault(dim.name, []).append(dim)
    return dimensions


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
        name: [name]
        for name in dimensions
        if not (name == "时间" and "月份" in dimensions)
    }
    for name, words in DIMENSION_SYNONYMS.items():
        if name in dimensions:
            synonyms.setdefault(name, [])
            synonyms[name].extend(words)

    for alias, standard in aliases.items():
        if standard == "时间" and "月份" in dimensions:
            standard = "月份"
        if standard in dimensions:
            synonyms.setdefault(standard, [])
            synonyms[standard].append(alias)

    return {
        name: sorted(set(words), key=len, reverse=True)
        for name, words in synonyms.items()
    }


def pick_dimensions(
    question: str, metric: Metric, dimensions: Dict[str, List[Dimension]], aliases: Dict[str, str]
) -> List[Dimension]:
    normalized = normalize_text(question)
    wanted = []

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


def load_distinct_values(db: MysqlCli, table: str, dimensions: Iterable[Dimension]) -> Dict[str, List[str]]:
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
    question: str, metric: Metric, dimensions: Dict[str, List[Dimension]], db: MysqlCli
) -> List[Tuple[str, str, str]]:
    all_table_dims = [dim for dim_list in dimensions.values() for dim in dim_list if dim.table == metric.table]
    distinct_values = load_distinct_values(db, metric.table, all_table_dims)
    dimension_names = set(dimensions.keys())
    filters = []
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


def month_bounds(year: int, start_month: int, end_month: int) -> Tuple[str, str]:
    if end_month == 12:
        end = f"{year + 1}-01-01"
    else:
        end = f"{year}-{end_month + 1:02d}-01"
    return f"{year}-{start_month:02d}-01", end


def parse_time_filter(question: str, table: str) -> Optional[Tuple[str, str]]:
    date_field = "order_date" if table == "sales_order" else "stat_month"
    match = re.search(r"(20\d{2})\s*年\s*(\d{1,2})\s*月?\s*(?:-|到|至|~)\s*(\d{1,2})\s*月", question)
    if match:
        year, start_month, end_month = map(int, match.groups())
        start, end = month_bounds(year, start_month, end_month)
        return date_field, f"{quote_ident(date_field)} >= {quote_literal(start)} AND {quote_ident(date_field)} < {quote_literal(end)}"

    match = re.search(r"(20\d{2})\s*年\s*(\d{1,2})\s*月", question)
    if match:
        year, month = map(int, match.groups())
        start, end = month_bounds(year, month, month)
        return date_field, f"{quote_ident(date_field)} >= {quote_literal(start)} AND {quote_ident(date_field)} < {quote_literal(end)}"

    match = re.search(r"(20\d{2})\s*年", question)
    if match:
        year = int(match.group(1))
        return date_field, f"{quote_ident(date_field)} >= {quote_literal(str(year) + '-01-01')} AND {quote_ident(date_field)} < {quote_literal(str(year + 1) + '-01-01')}"

    return None


def parse_limit(question: str) -> Optional[int]:
    match = re.search(r"(?:top|前)\s*(\d+)", question, re.IGNORECASE)
    if match:
        return max(1, min(int(match.group(1)), 100))
    if any(word in question for word in ["最高", "最低", "第一"]):
        return 1
    return None


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


def make_plan(question: str, db: MysqlCli) -> SemanticPlan:
    metrics = load_metrics(db)
    aliases = load_aliases(db)
    dimensions = load_dimensions(db)
    metric = pick_metric(question, metrics, aliases)
    picked_dimensions = pick_dimensions(question, metric, dimensions, aliases)
    filters = parse_filters(question, metric, dimensions, db)
    time_filter = parse_time_filter(question, metric.table)
    order_by = bool(picked_dimensions) and any(
        word in question for word in ["排行", "排名", "最高", "最低", "top", "Top", "对比"]
    )
    limit = parse_limit(question)
    plan = SemanticPlan(
        question=question,
        metric=metric,
        dimensions=picked_dimensions,
        filters=filters,
        time_filter=time_filter,
        order_by_metric_desc=order_by,
        limit=limit,
        sql="",
    )
    plan.sql = build_sql(plan)
    return plan


def print_table(rows: Sequence[Dict[str, str]]) -> None:
    if not rows:
        print("(no rows)")
        return
    headers = list(rows[0].keys())
    widths = {
        header: max(len(header), *(len(str(row.get(header, ""))) for row in rows))
        for header in headers
    }
    print(" | ".join(header.ljust(widths[header]) for header in headers))
    print("-+-".join("-" * widths[header] for header in headers))
    for row in rows:
        print(" | ".join(str(row.get(header, "")).ljust(widths[header]) for header in headers))


def numeric_value(value: object) -> float:
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return 0.0


def infer_chart_type(rows: Sequence[Dict[str, str]], dimension_columns: Sequence[str]) -> str:
    if not rows or not dimension_columns:
        return "table"
    if any(column == "月份" for column in dimension_columns):
        return "line"
    return "bar"


def build_chart_points(rows: Sequence[Dict[str, str]]) -> Tuple[List[str], List[float], str, List[str]]:
    if not rows:
        return [], [], "指标", []
    columns = list(rows[0].keys())
    metric_column = columns[-1]
    dimension_columns = columns[:-1]
    labels = []
    values = []
    for row in rows:
        label_parts = [str(row.get(column, "")) for column in dimension_columns]
        labels.append(" / ".join(part for part in label_parts if part) or metric_column)
        values.append(numeric_value(row.get(metric_column)))
    return labels, values, metric_column, dimension_columns


def render_svg_chart(
    title: str,
    rows: Sequence[Dict[str, str]],
    chart_type: str,
) -> str:
    labels, values, metric_column, _ = build_chart_points(rows)
    if not labels:
        return "<p class=\"empty\">没有可绘制的数据</p>"

    width = 960
    height = 460
    left = 72
    right = 32
    top = 48
    bottom = 104
    plot_width = width - left - right
    plot_height = height - top - bottom
    max_value = max(values) if values else 0
    max_value = max_value if max_value > 0 else 1

    def x_at(index: int) -> float:
        if len(labels) == 1:
            return left + plot_width / 2
        return left + (plot_width * index / (len(labels) - 1))

    def y_at(value: float) -> float:
        return top + plot_height - (value / max_value * plot_height)

    parts = [
        f"<svg viewBox=\"0 0 {width} {height}\" role=\"img\" aria-label=\"{html.escape(title)}\">",
        f"<text x=\"{left}\" y=\"28\" class=\"title\">{html.escape(title)}</text>",
        f"<line x1=\"{left}\" y1=\"{top}\" x2=\"{left}\" y2=\"{top + plot_height}\" class=\"axis\" />",
        f"<line x1=\"{left}\" y1=\"{top + plot_height}\" x2=\"{left + plot_width}\" y2=\"{top + plot_height}\" class=\"axis\" />",
    ]

    for step in range(5):
        value = max_value * step / 4
        y = y_at(value)
        parts.append(f"<line x1=\"{left}\" y1=\"{y:.2f}\" x2=\"{left + plot_width}\" y2=\"{y:.2f}\" class=\"grid\" />")
        parts.append(f"<text x=\"{left - 10}\" y=\"{y + 4:.2f}\" text-anchor=\"end\" class=\"tick\">{value:.0f}</text>")

    if chart_type == "line":
        points = " ".join(f"{x_at(index):.2f},{y_at(value):.2f}" for index, value in enumerate(values))
        parts.append(f"<polyline points=\"{points}\" class=\"line\" />")
        for index, value in enumerate(values):
            x = x_at(index)
            y = y_at(value)
            parts.append(f"<circle cx=\"{x:.2f}\" cy=\"{y:.2f}\" r=\"5\" class=\"point\" />")
            parts.append(f"<text x=\"{x:.2f}\" y=\"{y - 10:.2f}\" text-anchor=\"middle\" class=\"value\">{value:.0f}</text>")
    else:
        gap = 16
        bar_width = max(16, (plot_width - gap * (len(labels) + 1)) / max(1, len(labels)))
        for index, value in enumerate(values):
            x = left + gap + index * (bar_width + gap)
            y = y_at(value)
            bar_height = top + plot_height - y
            parts.append(f"<rect x=\"{x:.2f}\" y=\"{y:.2f}\" width=\"{bar_width:.2f}\" height=\"{bar_height:.2f}\" class=\"bar\" />")
            parts.append(f"<text x=\"{x + bar_width / 2:.2f}\" y=\"{y - 8:.2f}\" text-anchor=\"middle\" class=\"value\">{value:.0f}</text>")

    for index, label in enumerate(labels):
        x = x_at(index) if chart_type == "line" else left + 16 + index * ((plot_width - 16) / max(1, len(labels)))
        short = label if len(label) <= 14 else label[:13] + "..."
        parts.append(f"<text x=\"{x:.2f}\" y=\"{top + plot_height + 28}\" text-anchor=\"middle\" class=\"xlabel\">{html.escape(short)}</text>")

    parts.append(f"<text x=\"{left + plot_width}\" y=\"{height - 16}\" text-anchor=\"end\" class=\"metric\">指标：{html.escape(metric_column)}</text>")
    parts.append("</svg>")
    return "\n".join(parts)


def write_chart_html(path: str, question: str, plan: SemanticPlan, rows: Sequence[Dict[str, str]]) -> None:
    labels, _, metric_column, dimension_columns = build_chart_points(rows)
    chart_type = infer_chart_type(rows, dimension_columns)
    chart_title = f"{question} - {metric_column}"
    svg = render_svg_chart(chart_title, rows, chart_type)
    payload = json.dumps(
        {
            "question": question,
            "sql": plan.sql,
            "chart_type": chart_type,
            "dimensions": dimension_columns,
            "metric": metric_column,
            "labels": labels,
            "rows": rows,
        },
        ensure_ascii=False,
        indent=2,
    )
    document = f"""<!doctype html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{html.escape(chart_title)}</title>
  <style>
    body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: #172033; background: #f7f8fb; }}
    main {{ max-width: 1080px; margin: 32px auto; padding: 0 24px; }}
    .panel {{ background: #fff; border: 1px solid #d9deea; border-radius: 8px; padding: 24px; box-shadow: 0 8px 28px rgba(25, 35, 65, 0.08); }}
    h1 {{ font-size: 22px; margin: 0 0 16px; }}
    pre {{ overflow: auto; background: #101827; color: #dbe7ff; padding: 16px; border-radius: 6px; font-size: 13px; }}
    svg {{ width: 100%; height: auto; display: block; }}
    .title {{ font-size: 20px; font-weight: 700; fill: #172033; }}
    .axis {{ stroke: #667085; stroke-width: 1.2; }}
    .grid {{ stroke: #e7eaf2; stroke-width: 1; }}
    .tick, .xlabel, .metric {{ fill: #667085; font-size: 12px; }}
    .bar {{ fill: #2f6fef; }}
    .line {{ fill: none; stroke: #2f6fef; stroke-width: 3; }}
    .point {{ fill: #ffffff; stroke: #2f6fef; stroke-width: 2.5; }}
    .value {{ fill: #172033; font-size: 12px; font-weight: 600; }}
    .empty {{ color: #667085; }}
  </style>
</head>
<body>
  <main>
    <section class=\"panel\">
      {svg}
      <h1>SQL</h1>
      <pre>{html.escape(plan.sql)}</pre>
      <h1>Data</h1>
      <pre>{html.escape(payload)}</pre>
    </section>
  </main>
</body>
</html>
"""
    with open(path, "w", encoding="utf-8") as file:
        file.write(document)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ChatBI natural-language semantic query")
    parser.add_argument("question", nargs="+", help="Chinese natural-language question")
    parser.add_argument("--show-sql", action="store_true", help="print generated SQL")
    parser.add_argument("--json", action="store_true", help="print rows as JSON")
    parser.add_argument("--chart-html", help="write a standalone HTML chart to this path")
    parser.add_argument("--host", default=DEFAULT_DB["host"])
    parser.add_argument("--port", default=DEFAULT_DB["port"])
    parser.add_argument("--user", default=DEFAULT_DB["user"])
    parser.add_argument("--password", default=DEFAULT_DB["password"])
    parser.add_argument("--database", default=DEFAULT_DB["database"])
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    config = {
        "host": args.host,
        "port": str(args.port),
        "user": args.user,
        "password": args.password,
        "database": args.database,
    }
    db = MysqlCli(config)
    question = " ".join(args.question)
    try:
        plan = make_plan(question, db)
        rows = db.query(plan.sql)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.show_sql:
        print(plan.sql)
        print()
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        print_table(rows)
    if args.chart_html:
        write_chart_html(args.chart_html, question, plan, rows)
        print(f"\nchart: {args.chart_html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
