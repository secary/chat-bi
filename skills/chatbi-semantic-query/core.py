from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str((Path(__file__).resolve().parent / "scripts").resolve()))

from _shared.db import MysqlCli, default_db  # noqa: E402
from _shared.runtime import ensure_active, resolve_db_config  # noqa: E402
from semantic_query import build_json_payload, make_plan, write_chart_html  # noqa: E402


@dataclass(frozen=True)
class QueryRequest:
    question: str
    chart_html: Optional[str] = None


def run_query(request: QueryRequest, context: Any = None) -> dict[str, Any]:
    ensure_active(context)
    db = MysqlCli(
        resolve_db_config(context, default_db()),
        cancelled=(
            (lambda: False) if context is None else getattr(context, "cancelled", lambda: False)
        ),
        timeout_seconds=30.0 if context is None else getattr(context, "timeout_seconds", 30.0),
    )
    plan = make_plan(request.question, db)
    ensure_active(context)
    rows = db.query(plan.sql)
    ensure_active(context)
    if request.chart_html:
        write_chart_html(request.chart_html, request.question, plan, rows)
    return build_json_payload(request.question, plan.sql, rows, plan=plan)
