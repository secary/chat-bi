#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
FRONTEND_EXTENSIONS = {".js", ".jsx", ".ts", ".tsx", ".cjs", ".mjs"}


def python_executable() -> str:
    configured = os.getenv("CHATBI_PYTHON")
    if configured:
        return configured
    unix_python = ROOT / ".venv/bin/python"
    if unix_python.exists():
        return str(unix_python)
    windows_python = ROOT / ".venv/Scripts/python.exe"
    if windows_python.exists():
        return str(windows_python)
    return sys.executable


def is_python_target(path: str) -> bool:
    return Path(path).suffix == ".py"


def is_frontend_target(path: str) -> bool:
    pure = Path(path)
    return pure.suffix in FRONTEND_EXTENSIONS and pure.parts[:1] == ("frontend",)


def to_frontend_arg(path: str) -> str:
    pure = Path(path)
    if pure.parts[:1] == ("frontend",):
        return pure.relative_to("frontend").as_posix()
    return pure.as_posix()


def default_targets() -> list[str]:
    return ["backend", "scripts", "tests", "frontend"]


def staged_targets() -> list[str]:
    proc = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def existing_targets(paths: Sequence[str]) -> list[str]:
    existing: list[str] = []
    for path in paths:
        if (ROOT / path).exists():
            existing.append(path)
    return existing


def run_command(cmd: list[str], cwd: Path | None = None) -> None:
    workdir = cwd or ROOT
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=workdir, check=True)


def restage(paths: Sequence[str]) -> None:
    if not paths:
        return
    run_command(["git", "add", *paths])


def format_python(paths: Sequence[str]) -> list[str]:
    targets = [path for path in paths if is_python_target(path) or (ROOT / path).is_dir()]
    if not targets:
        return []
    python = python_executable()
    run_command([python, "-m", "ruff", "check", "--fix", *targets])
    run_command([python, "-m", "black", *targets])
    return list(targets)


def format_frontend(paths: Sequence[str]) -> list[str]:
    targets = [path for path in paths if is_frontend_target(path) or path == "frontend"]
    if not targets:
        return []
    args = [to_frontend_arg(path) for path in targets]
    run_command(["npm", "exec", "eslint", "--", "--fix", *args], cwd=ROOT / "frontend")
    return list(targets)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Format ChatBI Python and frontend files locally.",
    )
    parser.add_argument("paths", nargs="*", help="Optional files or directories to format.")
    parser.add_argument(
        "--staged",
        action="store_true",
        help="Format only staged added/copied/modified files and re-stage them.",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.staged:
        targets = existing_targets(staged_targets())
    elif args.paths:
        targets = existing_targets(args.paths)
    else:
        targets = default_targets()

    python_targets = [path for path in targets if is_python_target(path) or (ROOT / path).is_dir()]
    frontend_targets = [path for path in targets if is_frontend_target(path) or path == "frontend"]

    touched: list[str] = []
    touched.extend(format_python(python_targets))
    touched.extend(format_frontend(frontend_targets))

    if args.staged:
        restage([path for path in touched if not (ROOT / path).is_dir()])

    if not touched:
        print("No matching Python or frontend files to format.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
