#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from _shared.db import MysqlCli, default_db, quote_ident, quote_literal
from _shared.output import skill_response

DEFAULT_DB = default_db()
SEMANTIC_TABLES = {
    "data_source_config",
    "field_dictionary",
    "metric_definition",
    "dimension_definition",
    "business_term",
    "alias_mapping",
}


def q(v: str) -> str:
    return quote_literal(v)


def list_tables(db: MysqlCli, database: str) -> List[Dict[str, str]]:
    return db.query(
        "SELECT TABLE_NAME AS table_name, TABLE_TYPE AS table_type "
        "FROM information_schema.TABLES "
        f"WHERE TABLE_SCHEMA = {q(database)} "
        "ORDER BY TABLE_TYPE, TABLE_NAME"
    )


def list_columns(db: MysqlCli, database: str) -> List[Dict[str, str]]:
    return db.query(
        "SELECT TABLE_NAME AS table_name, COLUMN_NAME AS column_name, "
        "COLUMN_TYPE AS column_type, ORDINAL_POSITION AS ordinal_position "
        "FROM information_schema.COLUMNS "
        f"WHERE TABLE_SCHEMA = {q(database)} "
        "ORDER BY TABLE_NAME, ORDINAL_POSITION"
    )


def group_columns(rows: List[Dict[str, str]]) -> Dict[str, List[Dict[str, str]]]:
    grouped: Dict[str, List[Dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(row["table_name"], []).append(
            {"name": row["column_name"], "type": row["column_type"]}
        )
    return grouped


def load_field_dictionary(db: MysqlCli, available: set[str]) -> Dict[str, Dict[str, str]]:
    if "field_dictionary" not in available:
        return {}
    rows = db.query(
        "SELECT table_name, field_name, business_name, business_meaning "
        "FROM field_dictionary"
    )
    return {
        f"{row['table_name']}.{row['field_name']}": row
        for row in rows
    }


def load_metrics(db: MysqlCli, available: set[str]) -> List[Dict[str, str]]:
    if "metric_definition" not in available:
        return []
    return db.query(
        "SELECT metric_name, metric_code, source_table, formula, default_dimensions "
        "FROM metric_definition ORDER BY id"
    )


def load_dimensions(db: MysqlCli, available: set[str]) -> List[Dict[str, str]]:
    if "dimension_definition" not in available:
        return []
    return db.query(
        "SELECT dimension_name, field_name, source_table "
        "FROM dimension_definition ORDER BY id"
    )


def safe_count(db: MysqlCli, table: str) -> Optional[int]:
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
    columns: List[Dict[str, str]],
    field_meta: Dict[str, Dict[str, str]],
    limit: int,
) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
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


def summarize_database(db: MysqlCli, database: str, column_limit: int) -> Dict[str, object]:
    tables = list_tables(db, database)
    available = {row["table_name"] for row in tables}
    columns = group_columns(list_columns(db, database))
    field_meta = load_field_dictionary(db, available)
    metrics = load_metrics(db, available)
    dimensions = load_dimensions(db, available)

    business_assets = []
    semantic_assets = []
    for row in tables:
        name = row["table_name"]
        asset = {
            "name": name,
            "type": row["table_type"],
            "row_count": safe_count(db, name),
            "columns": enrich_columns(name, columns.get(name, []), field_meta, column_limit),
            "column_count": len(columns.get(name, [])),
        }
        if name in SEMANTIC_TABLES:
            semantic_assets.append(asset)
        else:
            business_assets.append(asset)

    return {
        "database": database,
        "business_assets": business_assets,
        "semantic_assets": semantic_assets,
        "metrics": metrics,
        "dimensions": dimensions,
    }


def render_text(summary: Dict[str, object]) -> str:
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
        col_names = "、".join(
            f"{c['business_name'] or c['name']}({c['name']})" for c in cols[:6]
        )
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


def database_overview(db: MysqlCli, database: str, column_limit: int = 8) -> Dict[str, object]:
    summary = summarize_database(db, database, column_limit)
    return skill_response(
        kind="database_overview",
        text=render_text(summary),
        data=summary,
    )


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize active ChatBI business database.")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--include-columns", type=int, default=8)
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
        result = database_overview(db, args.database, max(1, args.include_columns))
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
