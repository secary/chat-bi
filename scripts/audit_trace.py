#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from typing import Sequence

from backend.agent.harness_audit import build_audit_report


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit a ChatBI harness trace by trace_id.")
    parser.add_argument("--trace-id", required=True, help="Trace ID to audit")
    parser.add_argument("--compact", action="store_true", help="Print summary only")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_audit_report(args.trace_id)
    if args.compact:
        print(
            json.dumps(
                {
                    "trace_id": report["trace_id"],
                    "status": report["status"],
                    "score": report["score"],
                    "issue_count": len(report["issues"]),
                    "summary": report["summary"],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
