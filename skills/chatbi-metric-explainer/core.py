from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _shared.db import MysqlCli, default_db, quote_literal  # noqa: E402
from _shared.output import skill_response  # noqa: E402
from _shared.runtime import context_cancelled, context_timeout, resolve_db_config  # noqa: E402


@dataclass(frozen=True)
class MetricDef:
    name: str
    code: str
    table: str
    formula: str
    caliber: str
    default_dimensions: str


@dataclass(frozen=True)
class MetricExplainerRequest:
    question: str


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", text).lower()


def load_metrics(db: MysqlCli) -> dict[str, MetricDef]:
    rows = db.query(
        "SELECT metric_name, metric_code, source_table, formula, business_caliber, default_dimensions "
        "FROM metric_definition"
    )
    metrics: dict[str, MetricDef] = {}
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


def load_aliases(db: MysqlCli) -> dict[str, str]:
    rows = db.query(
        "SELECT alias_name, standard_name FROM alias_mapping WHERE object_type = '指标'"
    )
    return {row["alias_name"]: row["standard_name"] for row in rows}


def pick_metric(
    question: str, metrics: dict[str, MetricDef], aliases: dict[str, str]
) -> MetricDef | None:
    normalized = normalize_text(question)
    candidates: list[tuple[int, MetricDef]] = []
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


def extract_formula_fields(formula: str) -> list[str]:
    fields = re.findall(r"([A-Za-z_][A-Za-z0-9_]*)", formula)
    ignored = {"SUM", "AVG", "COUNT", "MIN", "MAX", "DISTINCT"}
    unique: list[str] = []
    for field in fields:
        if field.upper() in ignored:
            continue
        if field not in unique:
            unique.append(field)
    return unique


def load_field_details(db: MysqlCli, table: str, fields: list[str]) -> list[dict[str, str]]:
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


def related_aliases(metric_name: str, aliases: dict[str, str]) -> list[str]:
    return sorted(
        [alias for alias, standard in aliases.items() if standard == metric_name], key=len
    )


def render_text(metric: MetricDef, aliases: list[str], fields: list[dict[str, str]]) -> str:
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


def explain_metric(question: str, db: MysqlCli) -> dict[str, object]:
    metrics = load_metrics(db)
    aliases = load_aliases(db)
    metric = pick_metric(question, metrics, aliases)
    if not metric:
        raise ValueError(
            "未识别到可解释的指标，请明确说明指标名称，例如：销售额、毛利率、目标完成率。"
        )
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


def run_metric_explainer(request: MetricExplainerRequest, context: Any = None) -> dict[str, Any]:
    db = MysqlCli(
        resolve_db_config(context, default_db()),
        cancelled=context_cancelled(context),
        timeout_seconds=context_timeout(context),
    )
    return explain_metric(request.question, db)
