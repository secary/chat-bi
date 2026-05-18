from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str((Path(__file__).resolve().parent / "scripts").resolve()))

from _shared.output import skill_response  # noqa: E402
from _shared.runtime import ensure_active  # noqa: E402
from _shared.trace import log_skill_event  # noqa: E402
from semantic_processing_core import parse_question, render_summary  # noqa: E402


@dataclass(frozen=True)
class SemanticProcessingRequest:
    question: str


def run_semantic_processing(
    request: SemanticProcessingRequest, context: Any = None
) -> dict[str, Any]:
    ensure_active(context)
    question = request.question.strip()
    if not question:
        raise ValueError("question is required")
    log_skill_event(
        "skill.chatbi-semantic-processing",
        "started",
        "semantic processing started",
        {"question": question[:160]},
    )
    query_intent = parse_question(question)
    ensure_active(context)
    payload = skill_response(
        "semantic_intent",
        render_summary(query_intent),
        {"query_intent": query_intent},
    )
    log_skill_event(
        "skill.chatbi-semantic-processing",
        "completed",
        "semantic processing completed",
        {
            "status": query_intent["status"],
            "metric_ids": [item["metric_id"] for item in query_intent["metrics"]],
            "dimension_ids": [item["dimension_id"] for item in query_intent["dimensions"]],
            "missing_slots": query_intent["missing_slots"],
        },
    )
    return payload
