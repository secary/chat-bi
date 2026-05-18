from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Optional, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _shared.runtime import load_local_module  # noqa: E402

_CORE = load_local_module(__file__, "core.py")
DatabaseOverviewRequest = _CORE.DatabaseOverviewRequest
run_database_overview = _CORE.run_database_overview


def parse_request_args(argv: Optional[Sequence[str]] = None) -> DatabaseOverviewRequest:
    parser = argparse.ArgumentParser(description="Summarize active ChatBI business database.")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--include-columns", type=int, default=8)
    parser.add_argument("--host")
    parser.add_argument("--port")
    parser.add_argument("--user")
    parser.add_argument("--password")
    parser.add_argument("--database")
    parser.add_argument("question", nargs="*", default=[])
    args = parser.parse_args(argv)
    return DatabaseOverviewRequest(
        question=" ".join(args.question) if args.question else "",
        include_columns=args.include_columns,
    )


def run(argv: Optional[Sequence[str]] = None, context: Any = None) -> dict[str, Any]:
    return run_database_overview(parse_request_args(argv), context)
