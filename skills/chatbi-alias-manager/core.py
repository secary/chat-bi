from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str((Path(__file__).resolve().parent / "scripts").resolve()))

from _shared.db import MysqlCli, default_db  # noqa: E402
from _shared.runtime import context_cancelled, context_timeout, resolve_db_config  # noqa: E402
from add_alias_mapping import (  # noqa: E402
    infer_object_type,
    init_sql_line,
    insert_alias,
)
from _shared.output import skill_response  # noqa: E402


@dataclass(frozen=True)
class AliasManagerRequest:
    alias: str
    standard: str
    object_type: Optional[str] = None
    description: Optional[str] = None


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
