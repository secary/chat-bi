from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str((Path(__file__).resolve().parent / "scripts").resolve()))

from _shared.db import MysqlCli, default_db  # noqa: E402
from _shared.runtime import (
    context_cancelled,
    context_timeout,
    ensure_active,
    resolve_db_config,
)  # noqa: E402
from database_overview import database_overview  # noqa: E402


@dataclass(frozen=True)
class DatabaseOverviewRequest:
    question: str = ""
    include_columns: int = 8


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
