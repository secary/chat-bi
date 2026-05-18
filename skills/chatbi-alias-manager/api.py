from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Optional, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _shared.runtime import load_local_module  # noqa: E402

_CORE = load_local_module(__file__, "core.py")
AliasManagerRequest = _CORE.AliasManagerRequest
run_alias_manager = _CORE.run_alias_manager


def parse_request_args(argv: Optional[Sequence[str]] = None) -> AliasManagerRequest:
    parser = argparse.ArgumentParser(description="Add ChatBI alias_mapping entries")
    parser.add_argument("--alias", required=True)
    parser.add_argument("--standard", required=True)
    parser.add_argument("--type", choices=["指标", "维度"])
    parser.add_argument("--description")
    parser.add_argument("--print-init-sql", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--host")
    parser.add_argument("--port")
    parser.add_argument("--user")
    parser.add_argument("--password")
    parser.add_argument("--database")
    args = parser.parse_args(argv)
    return AliasManagerRequest(
        alias=args.alias,
        standard=args.standard,
        object_type=args.type,
        description=args.description,
    )


def run(argv: Optional[Sequence[str]] = None, context: Any = None) -> dict[str, Any]:
    return run_alias_manager(parse_request_args(argv), context)
