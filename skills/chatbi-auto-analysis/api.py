from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any, Optional, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _shared.runtime import load_local_module  # noqa: E402

_CORE = load_local_module(__file__, "core.py")
AutoAnalysisRequest = _CORE.AutoAnalysisRequest
run_auto_analysis = _CORE.run_auto_analysis


def parse_request_args(argv: Optional[Sequence[str]] = None) -> AutoAnalysisRequest:
    parser = argparse.ArgumentParser(description="Auto-analyze uploaded table rows")
    parser.add_argument("input_terms", nargs="*", help="Question or JSON payload string")
    parser.add_argument("--input", help="Question or JSON payload; overrides positional args")
    parser.add_argument("--input-file", help="Read question/rows JSON payload from a file")
    parser.add_argument("--json", action="store_true", help="Print structured SkillResult JSON")
    args = parser.parse_args(argv)
    if args.input_file:
        raw_input = Path(args.input_file).read_text(encoding="utf-8")
    else:
        raw_input = args.input if args.input is not None else " ".join(args.input_terms)
    return AutoAnalysisRequest(raw_input=raw_input)


def run(argv: Optional[Sequence[str]] = None, context: Any = None) -> dict[str, Any]:
    return run_auto_analysis(parse_request_args(argv), context)
