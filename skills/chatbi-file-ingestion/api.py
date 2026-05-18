from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Optional, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _shared.runtime import load_local_module  # noqa: E402

_CORE = load_local_module(__file__, "core.py")
FileIngestionRequest = _CORE.FileIngestionRequest
run_file_ingestion = _CORE.run_file_ingestion


def parse_request_args(argv: Optional[Sequence[str]] = None) -> FileIngestionRequest:
    parser = argparse.ArgumentParser(description="Inspect an uploaded ChatBI CSV/XLSX file.")
    parser.add_argument("file_path")
    parser.add_argument("--table", choices=sorted(_CORE._SCRIPT.SCHEMAS.keys()))
    parser.add_argument("--sample-size", type=int, default=5)
    parser.add_argument("--include-rows", action="store_true")
    parser.add_argument("--question", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    return FileIngestionRequest(
        input_path=args.file_path,
        question=str(args.question or "") or None,
        include_rows=bool(args.include_rows),
        requested_table=args.table,
        sample_size=args.sample_size,
    )


def run(argv: Optional[Sequence[str]] = None, context: Any = None) -> dict[str, Any]:
    return run_file_ingestion(parse_request_args(argv), context)
