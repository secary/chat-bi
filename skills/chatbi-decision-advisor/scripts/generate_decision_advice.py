#!/usr/bin/env python3
"""
Generate rule-based ChatBI decision advice from demo MySQL metrics.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Optional, Sequence

CURRENT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CURRENT_DIR))
sys.path.insert(0, str(CURRENT_DIR.parents[1]))

from _shared.db import MysqlCli, default_db
from decision_advisor_core import (
    build_advices,
    build_kpis,
    build_payload,
    build_scope,
    dump_payload,
    load_facts,
    parse_focus_dimensions,
    parse_focus_metrics,
    render_markdown,
)

DEFAULT_DB = default_db()


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate ChatBI decision advice")
    parser.add_argument("question_terms", nargs="*", help="Optional Chinese scope, such as 华东2026年4月决策建议")
    parser.add_argument("--question", help="Optional Chinese scope; overrides positional question")
    parser.add_argument("--json", action="store_true", help="print structured JSON")
    parser.add_argument("--host", default=DEFAULT_DB["host"])
    parser.add_argument("--port", default=DEFAULT_DB["port"])
    parser.add_argument("--user", default=DEFAULT_DB["user"])
    parser.add_argument("--password", default=DEFAULT_DB["password"])
    parser.add_argument("--database", default=DEFAULT_DB["database"])
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    db = MysqlCli(
        {
            "host": args.host,
            "port": str(args.port),
            "user": args.user,
            "password": args.password,
            "database": args.database,
        }
    )
    question = args.question if args.question is not None else " ".join(args.question_terms)
    try:
        facts = load_facts(db, build_scope(db, question))
        advices = build_advices(facts)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(dump_payload(build_payload(facts, advices)) if args.json else render_markdown(facts, advices))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
