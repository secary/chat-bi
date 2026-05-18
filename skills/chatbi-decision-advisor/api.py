from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Optional, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _shared.runtime import load_local_module  # noqa: E402

_CORE = load_local_module(__file__, "core.py")
DecisionAdvisorRequest = _CORE.DecisionAdvisorRequest
run_decision_advisor = _CORE.run_decision_advisor


def parse_request_args(argv: Optional[Sequence[str]] = None) -> DecisionAdvisorRequest:
    parser = argparse.ArgumentParser(description="Generate ChatBI decision advice")
    parser.add_argument("question_terms", nargs="*", help="Optional Chinese scope")
    parser.add_argument("--question", help="Optional Chinese scope; overrides positional question")
    parser.add_argument("--json", action="store_true", help="print structured JSON")
    parser.add_argument("--host")
    parser.add_argument("--port")
    parser.add_argument("--user")
    parser.add_argument("--password")
    parser.add_argument("--database")
    args = parser.parse_args(argv)
    question = args.question if args.question is not None else " ".join(args.question_terms)
    return DecisionAdvisorRequest(question=question)


def run(argv: Optional[Sequence[str]] = None, context: Any = None) -> dict[str, Any]:
    return run_decision_advisor(parse_request_args(argv), context)
