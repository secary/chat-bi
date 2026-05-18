from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Optional, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _shared.runtime import load_local_module  # noqa: E402

_CORE = load_local_module(__file__, "core.py")
ComparisonRequest = _CORE.ComparisonRequest
run_comparison = _CORE.run_comparison


def parse_request_args(argv: Optional[Sequence[str]] = None) -> ComparisonRequest:
    parser = argparse.ArgumentParser()
    parser.add_argument("question")
    parser.add_argument("--json", action="store_true", dest="json_out")
    args = parser.parse_args(argv)
    return ComparisonRequest(question=args.question)


def run(argv: Optional[Sequence[str]] = None, context: Any = None) -> dict[str, Any]:
    return run_comparison(parse_request_args(argv), context)
