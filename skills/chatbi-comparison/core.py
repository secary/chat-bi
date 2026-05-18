from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _shared.db import MysqlCli, default_db  # noqa: E402
from _shared.runtime import context_cancelled, context_timeout, resolve_db_config  # noqa: E402
import chatbi_comparison as comparison  # noqa: E402


@dataclass(frozen=True)
class ComparisonRequest:
    question: str


def run_comparison(request: ComparisonRequest, context: Any = None) -> dict[str, Any]:
    db = MysqlCli(
        resolve_db_config(context, default_db()),
        cancelled=context_cancelled(context),
        timeout_seconds=context_timeout(context),
    )
    question = request.question
    metric_name, metric_meta = comparison.detect_metric(question)
    dim_name, dim_field = comparison.detect_dimension(question)
    mode = comparison.detect_mode(question)
    year = comparison.detect_year(question)
    if mode == "all_months":
        return comparison.run_all_months(db, metric_meta, metric_name, year)
    if mode == "quarterly":
        return comparison.run_quarterly(db, metric_meta, metric_name, year)
    _, cur_month, prev_month = comparison.detect_months(question, db)
    return comparison.run_month_pair(
        db, metric_meta, dim_field, dim_name, metric_name, year, cur_month, prev_month
    )
