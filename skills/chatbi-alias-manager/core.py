from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _shared.db import MysqlCli, default_db, quote_literal  # noqa: E402
from _shared.output import skill_response  # noqa: E402
from _shared.runtime import context_cancelled, context_timeout, resolve_db_config  # noqa: E402


@dataclass(frozen=True)
class AliasManagerRequest:
    alias: str
    standard: str
    object_type: Optional[str] = None
    description: Optional[str] = None


def load_standard_names(db: MysqlCli) -> dict[str, str]:
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
    return f"('{alias_name}', '{standard_name}', '{object_type}', '{description}')"


def run_alias_manager(request: AliasManagerRequest, context: Any = None) -> dict[str, Any]:
    db = MysqlCli(
        resolve_db_config(context, default_db()),
        cancelled=context_cancelled(context),
        timeout_seconds=context_timeout(context),
    )
    object_type = infer_object_type(db, request.standard, request.object_type)
    description = request.description or f"{request.alias}统一映射到{request.standard}{object_type}"
    inserted = insert_alias(db, request.alias, request.standard, object_type, description)
    status = "inserted" if inserted else "exists"
    return skill_response(
        kind="alias",
        text=f"{status}: {request.alias} -> {request.standard} ({object_type})",
        data={
            "status": status,
            "alias": request.alias,
            "standard": request.standard,
            "object_type": object_type,
            "init_sql": init_sql_line(request.alias, request.standard, object_type, description),
        },
    )
