#!/usr/bin/env python3
"""
Add ChatBI semantic aliases to alias_mapping.

This script is intentionally small and deterministic: it validates that the
target standard metric/dimension exists, then inserts a missing alias into the
demo MySQL metadata table. It uses the local `mysql` CLI, so no Python MySQL
package is required.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from _shared.db import MysqlCli, default_db, quote_literal
from _shared.output import skill_response

DEFAULT_DB = default_db()


def load_standard_names(db: MysqlCli) -> Dict[str, str]:
    rows = db.query(
        "SELECT metric_name AS name, '指标' AS object_type FROM metric_definition "
        "UNION "
        "SELECT dimension_name AS name, '维度' AS object_type FROM dimension_definition "
        "UNION "
        "SELECT '月份' AS name, '维度' AS object_type"
    )
    return {row["name"]: row["object_type"] for row in rows}


def infer_object_type(db: MysqlCli, standard_name: str, object_type: Optional[str]) -> str:
    standards = load_standard_names(db)
    if standard_name not in standards:
        valid = "、".join(sorted(standards))
        raise ValueError(f"标准名不存在: {standard_name}. 可用标准名: {valid}")
    inferred = standards[standard_name]
    if object_type and object_type != inferred:
        raise ValueError(f"{standard_name} 是{inferred}，不是{object_type}")
    return inferred


def existing_alias(db: MysqlCli, alias_name: str, standard_name: str, object_type: str) -> bool:
    rows = db.query(
        "SELECT id FROM alias_mapping "
        f"WHERE alias_name = {quote_literal(alias_name)} "
        f"AND standard_name = {quote_literal(standard_name)} "
        f"AND object_type = {quote_literal(object_type)} "
        "LIMIT 1"
    )
    return bool(rows)


def insert_alias(
    db: MysqlCli,
    alias_name: str,
    standard_name: str,
    object_type: str,
    description: Optional[str],
) -> bool:
    if existing_alias(db, alias_name, standard_name, object_type):
        return False
    desc = description or f"{alias_name}统一映射到{standard_name}{object_type}"
    db.query(
        "INSERT INTO alias_mapping "
        "(alias_name, standard_name, object_type, description) VALUES "
        f"({quote_literal(alias_name)}, {quote_literal(standard_name)}, "
        f"{quote_literal(object_type)}, {quote_literal(desc)})"
    )
    return True


def init_sql_line(alias_name: str, standard_name: str, object_type: str, description: str) -> str:
    return (
        f"('{alias_name}', '{standard_name}', '{object_type}', "
        f"'{description}')"
    )


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Add ChatBI alias_mapping entries")
    parser.add_argument("--alias", required=True, help="New synonym, such as 成交方式")
    parser.add_argument("--standard", required=True, help="Existing standard metric/dimension name")
    parser.add_argument("--type", choices=["指标", "维度"], help="Optional object type")
    parser.add_argument("--description", help="Optional business description")
    parser.add_argument(
        "--print-init-sql",
        action="store_true",
        help="Print VALUES tuple for database/init.sql",
    )
    parser.add_argument("--json", action="store_true", help="print structured SkillResult JSON")
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
    try:
        object_type = infer_object_type(db, args.standard, args.type)
        description = args.description or f"{args.alias}统一映射到{args.standard}{object_type}"
        inserted = insert_alias(db, args.alias, args.standard, object_type, description)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    status = "inserted" if inserted else "exists"
    text = f"{status}: {args.alias} -> {args.standard} ({object_type})"
    if args.json:
        payload = skill_response(
            kind="alias",
            text=text,
            data={
                "status": status,
                "alias": args.alias,
                "standard": args.standard,
                "object_type": object_type,
                "init_sql": init_sql_line(args.alias, args.standard, object_type, description),
            },
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    print(text)
    if args.print_init_sql:
        print(init_sql_line(args.alias, args.standard, object_type, description))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
