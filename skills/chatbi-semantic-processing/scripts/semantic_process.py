#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, Sequence

CURRENT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CURRENT_DIR))
sys.path.insert(0, str(CURRENT_DIR.parents[1]))

from _shared.output import skill_response
from _shared.trace import log_skill_event
from semantic_processing_core import parse_question, render_summary


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize banking BI question to Query Intent JSON")
    parser.add_argument("question_terms", nargs="*", help="Chinese banking BI question")
    parser.add_argument("--question", help="Optional full question; overrides positional args")
    parser.add_argument("--json", action="store_true", help="Print structured SkillResult JSON")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    question = (args.question if args.question is not None else " ".join(args.question_terms)).strip()
    if not question:
        print("ERROR: question is required", file=sys.stderr)
        return 1

    log_skill_event("skill.chatbi-semantic-processing", "started", "semantic processing started", {"question": question[:160]})
    query_intent = parse_question(question)
    payload = skill_response("semantic_intent", render_summary(query_intent), {"query_intent": query_intent})
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
    print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else payload["text"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
