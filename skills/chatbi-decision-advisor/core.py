from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _shared.db import MysqlCli, default_db  # noqa: E402
from _shared.runtime import (
    context_cancelled,
    context_timeout,
    ensure_active,
    resolve_db_config,
)  # noqa: E402
import decision_advisor_core as advisor_core  # noqa: E402


@dataclass(frozen=True)
class DecisionAdvisorRequest:
    question: str


def parse_focus_dimensions(question: str) -> list[str]:
    return advisor_core.parse_focus_dimensions(question)


def parse_focus_metrics(question: str) -> list[str]:
    return advisor_core.parse_focus_metrics(question)


def build_advices(facts: dict[str, object]) -> list[advisor_core.Advice]:
    return advisor_core.build_advices(facts)


def run_decision_advisor(request: DecisionAdvisorRequest, context: Any = None) -> dict[str, Any]:
    ensure_active(context)
    db = MysqlCli(
        resolve_db_config(context, default_db()),
        cancelled=context_cancelled(context),
        timeout_seconds=context_timeout(context),
    )
    facts = advisor_core.load_facts(db, advisor_core.build_scope(db, request.question))
    ensure_active(context)
    advices = build_advices(facts)
    return advisor_core.build_payload(facts, advices)
