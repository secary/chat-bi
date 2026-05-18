#!/usr/bin/env python3
"""
Add ChatBI semantic aliases to alias_mapping.

This script is intentionally small and deterministic: it validates that the
target standard metric/dimension exists, then inserts a missing alias into the
demo MySQL metadata table. It uses the local `mysql` CLI, so no Python MySQL
package is required.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, Optional, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from _shared.runtime import load_local_module
from _shared.db import MysqlCli, quote_literal


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
    return f"('{alias_name}', '{standard_name}', '{object_type}', " f"'{description}')"


def main(argv: Optional[Sequence[str]] = None) -> int:
    tokens = list(sys.argv[1:] if argv is None else argv)
    api_module = load_local_module(__file__, "../api.py")
    try:
        request = api_module.parse_request_args(tokens)
        payload = api_module.run_alias_manager(request)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if "--json" in tokens:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    print(payload["text"])
    if "--print-init-sql" in tokens:
        print(payload["data"]["init_sql"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
