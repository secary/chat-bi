from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _shared.runtime import ensure_active, load_local_module  # noqa: E402

_SCRIPT = load_local_module(__file__, "scripts/inspect_uploaded_table.py")


@dataclass(frozen=True)
class FileIngestionRequest:
    input_path: str
    question: Optional[str] = None
    include_rows: bool = False
    requested_table: Optional[str] = None
    sample_size: int = 5


def run_file_ingestion(request: FileIngestionRequest, context: Any = None) -> dict[str, Any]:
    ensure_active(context)
    return _SCRIPT.inspect_file(
        Path(request.input_path),
        request.requested_table,
        request.sample_size,
        request.include_rows,
        question=request.question or "",
        context=context,
    )
