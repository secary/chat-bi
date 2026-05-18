from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Optional, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _shared.runtime import load_local_module  # noqa: E402

_CORE = load_local_module(__file__, "core.py")
QueryRequest = _CORE.QueryRequest
run_query = _CORE.run_query


def parse_request_args(argv: Optional[Sequence[str]] = None) -> QueryRequest:
    parser = argparse.ArgumentParser(description="ChatBI natural-language semantic query")
    parser.add_argument("question", nargs="+", help="Chinese natural-language question")
    parser.add_argument("--show-sql", action="store_true", help="print generated SQL")
    parser.add_argument("--json", action="store_true", help="print rows as JSON")
    parser.add_argument("--chart-html", help="write a standalone HTML chart to this path")
    parser.add_argument("--host")
    parser.add_argument("--port")
    parser.add_argument("--user")
    parser.add_argument("--password")
    parser.add_argument("--database")
    args = parser.parse_args(argv)
    return QueryRequest(question=" ".join(args.question), chart_html=args.chart_html)


def run(argv: Optional[Sequence[str]] = None, context: Any = None) -> dict[str, Any]:
    return run_query(parse_request_args(argv), context)
