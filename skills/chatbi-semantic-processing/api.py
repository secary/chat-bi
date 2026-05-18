from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Optional, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _shared.runtime import load_local_module  # noqa: E402

_CORE = load_local_module(__file__, "core.py")
SemanticProcessingRequest = _CORE.SemanticProcessingRequest
run_semantic_processing = _CORE.run_semantic_processing


def parse_request_args(argv: Optional[Sequence[str]] = None) -> SemanticProcessingRequest:
    parser = argparse.ArgumentParser(
        description="Normalize banking BI question to Query Intent JSON"
    )
    parser.add_argument("question_terms", nargs="*", help="Chinese banking BI question")
    parser.add_argument("--question", help="Optional full question; overrides positional args")
    parser.add_argument("--json", action="store_true", help="Print structured SkillResult JSON")
    args = parser.parse_args(argv)
    question = (
        args.question if args.question is not None else " ".join(args.question_terms)
    ).strip()
    return SemanticProcessingRequest(question=question)


def run(argv: Optional[Sequence[str]] = None, context: Any = None) -> dict[str, Any]:
    return run_semantic_processing(parse_request_args(argv), context)
