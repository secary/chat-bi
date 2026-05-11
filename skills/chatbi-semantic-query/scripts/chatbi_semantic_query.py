#!/usr/bin/env python3
"""
Lightweight ChatBI semantic query script.

It maps a Chinese natural-language question to governed metric SQL using the
metadata tables in the demo MySQL database, then executes the generated query.
No Python MySQL package is required; the script uses the local `mysql` CLI.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Optional, Sequence

CURRENT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CURRENT_DIR))
sys.path.insert(0, str(CURRENT_DIR.parents[1]))

from _shared.db import MysqlCli, default_db  # noqa: E402
from semantic_query import (  # noqa: E402
    build_json_payload,
    make_plan,
    print_table,
    write_chart_html,
)

DEFAULT_DB = default_db()


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ChatBI natural-language semantic query")
    parser.add_argument("question", nargs="+", help="Chinese natural-language question")
    parser.add_argument("--show-sql", action="store_true", help="print generated SQL")
    parser.add_argument("--json", action="store_true", help="print rows as JSON")
    parser.add_argument("--chart-html", help="write a standalone HTML chart to this path")
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
    question = " ".join(args.question)
    try:
        plan = make_plan(question, db)
        rows = db.query(plan.sql)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.show_sql:
        print(plan.sql)
        print()
    if args.json:
        print(
            json.dumps(
                build_json_payload(question, plan.sql, rows, plan=plan),
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print_table(rows)
    if args.chart_html:
        write_chart_html(args.chart_html, question, plan, rows)
        print(f"\nchart: {args.chart_html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
