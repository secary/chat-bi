#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from _shared.db import MysqlCli, default_db, quote_literal
from _shared.output import skill_response

DEFAULT_DB = default_db()


@dataclass(frozen=True)
class MetricDef:
    name: str
    code: str
    table: str
    formula: str
    caliber: str
    default_dimensions: str


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", text).lower()


def load_metrics(db: MysqlCli) -> Dict[str, MetricDef]:
    rows = db.query(
        "SELECT metric_name, metric_code, source_table, formula, business_caliber, default_dimensions "
        "FROM metric_definition"
    )
    metrics: Dict[str, MetricDef] = {}
    for row in rows:
        metric = MetricDef(
            name=row["metric_name"],
            code=row["metric_code"],
            table=row["source_table"],
            formula=row["formula"],
            caliber=row["business_caliber"],
            default_dimensions=row["default_dimensions"],
        )
        metrics[metric.name] = metric
        metrics[metric.code] = metric
    return metrics


def load_aliases(db: MysqlCli) -> Dict[str, str]:
    rows = db.query(
        "SELECT alias_name, standard_name FROM alias_mapping WHERE object_type = '指标'"
    )
    return {row["alias_name"]: row["standard_name"] for row in rows}


def pick_metric(question: str, metrics: Dict[str, MetricDef], aliases: Dict[str, str]) -> Optional[MetricDef]:
    normalized = normalize_text(question)
    candidates: List[tuple[int, MetricDef]] = []
    for alias, standard in aliases.items():
        metric = metrics.get(standard)
        if metric and normalize_text(alias) in normalized:
            candidates.append((len(alias), metric))
    for key, metric in metrics.items():
        if normalize_text(key) in normalized:
            candidates.append((len(key), metric))
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: item[0], reverse=True)[0][1]


def extract_formula_fields(formula: str) -> List[str]:
    fields = re.findall(r"([A-Za-z_][A-Za-z0-9_]*)", formula)
    ignored = {"SUM", "AVG", "COUNT", "MIN", "MAX", "DISTINCT"}
    unique: List[str] = []
    for field in fields:
        if field.upper() in ignored:
            continue
        if field not in unique:
            unique.append(field)
    return unique


def load_field_details(db: MysqlCli, table: str, fields: List[str]) -> List[Dict[str, str]]:
    if not fields:
        return []
    field_list = ", ".join(quote_literal(field) for field in fields)
    sql = (
        "SELECT field_name, business_name, business_meaning, example_value "
        "FROM field_dictionary "
        f"WHERE table_name = {quote_literal(table)} AND field_name IN ({field_list})"
    )
    rows = db.query(sql)
    order = {field: index for index, field in enumerate(fields)}
    return sorted(rows, key=lambda row: order.get(row["field_name"], 999))


def related_aliases(metric_name: str, aliases: Dict[str, str]) -> List[str]:
    return sorted([alias for alias, standard in aliases.items() if standard == metric_name], key=len)


def render_text(metric: MetricDef, aliases: List[str], fields: List[Dict[str, str]]) -> str:
    lines = [
        f"## 指标解释：{metric.name}",
        "",
        f"- 指标编码：`{metric.code}`",
        f"- 来源表：`{metric.table}`",
        f"- 统计口径：{metric.caliber}",
        f"- 计算公式：`{metric.formula}`",
        f"- 常用分析维度：{metric.default_dimensions}",
    ]
    if aliases:
        lines.append(f"- 常见别名：{', '.join(aliases)}")
    if fields:
        lines.extend(["", "### 相关字段", ""])
        for field in fields:
            lines.append(
                f"- `{field['field_name']}` / {field['business_name']}：{field['business_meaning']}（示例：{field['example_value']}）"
            )
    lines.extend(
        [
            "",
            "### 使用建议",
            "",
            "- 如果你想查这个指标的实际数值，可以继续直接提问，例如：`按区域看2026年1-4月"
            f"{metric.name}排行`。",
        ]
    )
    return "\n".join(lines)


def explain_metric(question: str, db: MysqlCli) -> Dict[str, object]:
    metrics = load_metrics(db)
    aliases = load_aliases(db)
    metric = pick_metric(question, metrics, aliases)
    if not metric:
        raise ValueError("未识别到可解释的指标，请明确说明指标名称，例如：销售额、毛利率、目标完成率。")
    fields = load_field_details(db, metric.table, extract_formula_fields(metric.formula))
    alias_list = related_aliases(metric.name, aliases)
    return skill_response(
        kind="metric_explanation",
        text=render_text(metric, alias_list, fields),
        data={
            "metric_name": metric.name,
            "metric_code": metric.code,
            "source_table": metric.table,
            "formula": metric.formula,
            "business_caliber": metric.caliber,
            "default_dimensions": metric.default_dimensions,
            "aliases": alias_list,
            "fields": fields,
        },
    )


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Explain a governed ChatBI metric.")
    parser.add_argument("question", nargs="+", help="Chinese metric explanation question")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--host", default=DEFAULT_DB["host"])
    parser.add_argument("--port", default=DEFAULT_DB["port"])
    parser.add_argument("--user", default=DEFAULT_DB["user"])
    parser.add_argument("--password", default=DEFAULT_DB["password"])
    parser.add_argument("--database", default=DEFAULT_DB["database"])
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    db = MysqlCli(
        {
            "host": args.host,
            "port": str(args.port),
            "user": args.user,
            "password": args.password,
            "database": args.database,
        }
    )
    try:
        result = explain_metric(" ".join(args.question), db)
    except Exception as exc:
        if args.json:
            print(json.dumps(skill_response("error", str(exc)), ensure_ascii=False))
            return 1
        print(f"错误：{exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result["text"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
