from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _shared.db import MysqlCli, default_db, quote_ident, quote_literal  # noqa: E402
from _shared.output import skill_response  # noqa: E402
from _shared.runtime import (  # noqa: E402
    context_cancelled,
    context_timeout,
    ensure_active,
    resolve_db_config,
)

SEMANTIC_TABLES = {
    "data_source_config",
    "field_dictionary",
    "metric_definition",
    "dimension_definition",
    "business_term",
    "alias_mapping",
}

INTERNAL_TABLE_PREFIXES = ("admin_", "app_")
INTERNAL_TABLES = {"log"}


@dataclass(frozen=True)
class DatabaseOverviewRequest:
    question: str = ""
    include_columns: int = 8


def q(value: str) -> str:
    return quote_literal(value)


def list_tables(db: MysqlCli, database: str) -> list[dict[str, str]]:
    return db.query(
        "SELECT TABLE_NAME AS table_name, TABLE_TYPE AS table_type "
        "FROM information_schema.TABLES "
        f"WHERE TABLE_SCHEMA = {q(database)} "
        "ORDER BY TABLE_TYPE, TABLE_NAME"
    )


def list_columns(db: MysqlCli, database: str) -> list[dict[str, str]]:
    return db.query(
        "SELECT TABLE_NAME AS table_name, COLUMN_NAME AS column_name, "
        "COLUMN_TYPE AS column_type, ORDINAL_POSITION AS ordinal_position "
        "FROM information_schema.COLUMNS "
        f"WHERE TABLE_SCHEMA = {q(database)} "
        "ORDER BY TABLE_NAME, ORDINAL_POSITION"
    )


def group_columns(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(row["table_name"], []).append(
            {"name": row["column_name"], "type": row["column_type"]}
        )
    return grouped


def load_field_dictionary(db: MysqlCli, available: set[str]) -> dict[str, dict[str, str]]:
    if "field_dictionary" not in available:
        return {}
    rows = db.query(
        "SELECT table_name, field_name, business_name, business_meaning FROM field_dictionary"
    )
    return {f"{row['table_name']}.{row['field_name']}": row for row in rows}


def load_metrics(db: MysqlCli, available: set[str]) -> list[dict[str, str]]:
    if "metric_definition" not in available:
        return []
    return db.query(
        "SELECT metric_name, metric_code, source_table, formula, default_dimensions "
        "FROM metric_definition ORDER BY id"
    )


def load_dimensions(db: MysqlCli, available: set[str]) -> list[dict[str, str]]:
    if "dimension_definition" not in available:
        return []
    return db.query(
        "SELECT dimension_name, field_name, source_table FROM dimension_definition ORDER BY id"
    )


def safe_count(db: MysqlCli, table: str) -> int | None:
    try:
        rows = db.query(f"SELECT COUNT(*) AS row_count FROM {quote_ident(table)}")
    except Exception:
        return None
    if not rows:
        return None
    try:
        return int(rows[0].get("row_count") or 0)
    except ValueError:
        return None


def enrich_columns(
    table: str,
    columns: list[dict[str, str]],
    field_meta: dict[str, dict[str, str]],
    limit: int,
) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for column in columns[:limit]:
        meta = field_meta.get(f"{table}.{column['name']}", {})
        out.append(
            {
                "name": column["name"],
                "type": column["type"],
                "business_name": meta.get("business_name", ""),
                "business_meaning": meta.get("business_meaning", ""),
            }
        )
    return out


def is_internal_app_table(table_name: str) -> bool:
    normalized = table_name.strip().lower()
    return normalized in INTERNAL_TABLES or normalized.startswith(INTERNAL_TABLE_PREFIXES)


def summarize_database(db: MysqlCli, database: str, column_limit: int) -> dict[str, object]:
    tables = list_tables(db, database)
    available = {row["table_name"] for row in tables}
    columns = group_columns(list_columns(db, database))
    field_meta = load_field_dictionary(db, available)
    metrics = load_metrics(db, available)
    dimensions = load_dimensions(db, available)

    business_assets = []
    semantic_assets = []
    hidden_assets = []
    for row in tables:
        name = row["table_name"]
        asset = {
            "name": name,
            "type": row["table_type"],
            "row_count": safe_count(db, name),
            "columns": enrich_columns(name, columns.get(name, []), field_meta, column_limit),
            "column_count": len(columns.get(name, [])),
        }
        if is_internal_app_table(name):
            hidden_assets.append(asset)
        elif name in SEMANTIC_TABLES:
            semantic_assets.append(asset)
        else:
            business_assets.append(asset)

    return {
        "database": database,
        "business_assets": business_assets,
        "semantic_assets": semantic_assets,
        "hidden_assets": hidden_assets,
        "hidden_asset_count": len(hidden_assets),
        "metrics": metrics,
        "dimensions": dimensions,
    }


def render_text(summary: dict[str, object]) -> str:
    business = summary["business_assets"]
    semantic = summary["semantic_assets"]
    metrics = summary["metrics"]
    assert isinstance(business, list)
    assert isinstance(semantic, list)
    assert isinstance(metrics, list)

    lines = [
        f"## 业务数据库概览：`{summary['database']}`",
        "",
        f"- 可直接查询的业务表/视图：{len(business)} 张",
        f"- 语义层元数据表：{len(semantic)} 张",
        f"- 已治理指标：{len(metrics)} 个",
        "",
        "### 可查询业务资产",
        "",
    ]
    for asset in business:
        cols = asset["columns"]
        assert isinstance(cols, list)
        col_names = "、".join(f"{c['business_name'] or c['name']}({c['name']})" for c in cols[:6])
        suffix = "..." if int(asset["column_count"]) > len(cols[:6]) else ""
        row_count = "未知" if asset["row_count"] is None else str(asset["row_count"])
        lines.append(
            f"- `{asset['name']}`：{asset['type']}，约 {row_count} 行，字段：{col_names}{suffix}"
        )

    if metrics:
        lines.extend(["", "### 可用指标", ""])
        metric_names = "、".join(str(row["metric_name"]) for row in metrics[:12])
        lines.append(f"- {metric_names}")

    lines.extend(
        [
            "",
            "### 你可以这样问",
            "",
            "- `按区域看业务规模排行`",
            "- `每月收入贡献趋势`",
            "- `解释一下目标完成率口径`",
        ]
    )
    return "\n".join(lines)


def database_overview(
    db: MysqlCli, database: str, column_limit: int = 8, question: str = ""
) -> dict[str, object]:
    summary = summarize_database(db, database, column_limit)
    return skill_response(
        kind="database_overview",
        text=render_text(summary),
        data=summary,
    )


def run_database_overview(request: DatabaseOverviewRequest, context: Any = None) -> dict[str, Any]:
    ensure_active(context)
    db_config = resolve_db_config(context, default_db())
    db = MysqlCli(
        db_config,
        cancelled=context_cancelled(context),
        timeout_seconds=context_timeout(context),
    )
    return database_overview(
        db,
        str(db_config["database"]),
        max(1, int(request.include_columns)),
        request.question,
    )
