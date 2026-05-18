from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str((Path(__file__).resolve().parent / "scripts").resolve()))

from _shared.db import MysqlCli, default_db  # noqa: E402
from _shared.runtime import context_cancelled, context_timeout, resolve_db_config  # noqa: E402
from explain_metric import explain_metric  # noqa: E402


@dataclass(frozen=True)
class MetricExplainerRequest:
    question: str


def run_metric_explainer(request: MetricExplainerRequest, context: Any = None) -> dict[str, Any]:
    db = MysqlCli(
        resolve_db_config(context, default_db()),
        cancelled=context_cancelled(context),
        timeout_seconds=context_timeout(context),
    )
    return explain_metric(request.question, db)
