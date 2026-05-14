#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]


def python_executable() -> str:
    configured = os.getenv("CHATBI_PYTHON")
    if configured:
        return configured
    project_python = ROOT / ".venv/bin/python"
    if project_python.exists():
        return str(project_python)
    return sys.executable


MODULE_SUITES: dict[str, list[str]] = {
    "foundation": [
        "tests/test_bootstrap_dev_script.py",
        "tests/test_config_db_defaults.py",
        "tests/test_env_loader.py",
        "tests/test_format_code_script.py",
        "tests/test_http_utils.py",
        "tests/test_observation.py",
        "tests/test_skill_result_log_payload.py",
        "tests/test_agent_skill_protocol.py",
        "tests/test_e2e_smoke_script.py",
        "tests/test_run_tests_script.py",
        "tests/test_trace.py",
    ],
    "skills": [
        "tests/test_auto_analysis_skill.py",
        "tests/test_chart_recommendation_skill.py",
        "tests/test_dashboard_orchestration_skill.py",
        "tests/test_database_overview_skill.py",
        "tests/test_decision_advisor_focus.py",
        "tests/test_file_ingestion_skill.py",
        "tests/test_metric_explainer_skill.py",
        "tests/test_semantic_query_core.py",
        "tests/test_semantic_processing_skill.py",
        "tests/test_skill_result_log_payload.py",
    ],
    "agent": [
        "tests/test_agent_runner_contract.py",
        "tests/test_agent_skill_protocol.py",
        "tests/test_agent_workflow.py",
        "tests/test_chat_route_disconnect.py",
        "tests/test_multi_agent_registry.py",
        "tests/test_multi_agent_manager.py",
        "tests/test_observation.py",
        "tests/test_query_advice_dimension_flow.py",
        "tests/test_react_runner.py",
        "tests/test_upload_context.py",
    ],
    "admin": [
        "tests/test_admin_multi_agents.py",
        "tests/test_app_llm_saved.py",
        "tests/test_config_db_defaults.py",
        "tests/test_chatbi_llm_fallback.py",
        "tests/test_db_mysql_targets.py",
        "tests/test_llm_profile_repo.py",
        "tests/test_multi_agent_registry.py",
        "tests/test_skill_registry_graceful.py",
    ],
    "auth-memory": [
        "tests/test_auth_deps_disabled.py",
        "tests/test_auth_password.py",
        "tests/test_auth_tokens.py",
        "tests/test_memory_repo_prompts.py",
        "tests/test_memory_service_off.py",
    ],
    "dashboard": [
        "tests/test_dashboard_overview.py",
        "tests/test_chart_renderer.py",
        "tests/test_kpi_renderer.py",
    ],
    "data-sources": [
        "tests/test_config_db_defaults.py",
        "tests/test_database_overview_skill.py",
        "tests/test_db_mysql_targets.py",
        "tests/test_executor_file_ingestion_args.py",
        "tests/test_external_bank_demo_sql.py",
        "tests/test_file_ingestion_skill.py",
    ],
    "upload-vision": [
        "tests/test_file_ingestion_skill.py",
        "tests/test_upload_context.py",
        "tests/test_vision_extract.py",
        "tests/test_vision_llm_runtime.py",
    ],
    "report": [
        "tests/test_report_pdf.py",
    ],
}

SUITE_ALIASES: dict[str, list[str]] = {
    "quick": ["foundation", "skills", "data-sources"],
    "backend": ["admin", "dashboard", "report"],
    "auth": ["auth-memory"],
    "data": ["data-sources"],
}


def discover_python_tests() -> list[str]:
    return sorted(
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "tests").glob("test_*.py")
        if path.is_file()
    )


def tests_for_groups(groups: Sequence[str]) -> list[str]:
    if "all" in groups:
        return discover_python_tests()
    seen: set[str] = set()
    out: list[str] = []
    for group in groups:
        suite_names = SUITE_ALIASES.get(group, [group])
        for suite in suite_names:
            for item in MODULE_SUITES[suite]:
                if item not in seen:
                    seen.add(item)
                    out.append(item)
    return out


def available_groups() -> list[str]:
    return [*MODULE_SUITES.keys(), *SUITE_ALIASES.keys(), "all"]


def manifest_items() -> list[str]:
    items: set[str] = set()
    for tests in MODULE_SUITES.values():
        items.update(tests)
    return sorted(items)


def missing_manifest_paths() -> list[str]:
    return [item for item in manifest_items() if not (ROOT / item).is_file()]


def suite_coverage_gaps() -> list[str]:
    covered = set(manifest_items())
    return [item for item in discover_python_tests() if item not in covered]


def run_command(cmd: list[str], env: dict[str, str], dry_run: bool) -> int:
    print("+ " + " ".join(cmd))
    if dry_run:
        return 0
    return subprocess.run(cmd, cwd=ROOT, env=env, check=False).returncode


def run_pytest(groups: Sequence[str], extra_args: Sequence[str], dry_run: bool) -> int:
    tests = tests_for_groups(groups)
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    cmd = [python_executable(), "-m", "pytest", *tests, *extra_args]
    return run_command(cmd, env, dry_run)


def run_frontend(dry_run: bool) -> int:
    cmd = ["npm", "run", "test"]
    print("+ cd frontend")
    if dry_run:
        print("+ " + " ".join(cmd))
        return 0
    return subprocess.run(cmd, cwd=ROOT / "frontend", check=False).returncode


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    raw = list(sys.argv[1:] if argv is None else argv)
    pytest_args: list[str] = []
    if "--" in raw:
        split_at = raw.index("--")
        pytest_args = raw[split_at + 1 :]
        raw = raw[:split_at]

    parser = argparse.ArgumentParser(description="ChatBI automated test runner.")
    parser.add_argument(
        "groups",
        nargs="*",
        default=["quick"],
        help="Feature module suites to run. Defaults to quick.",
    )
    parser.add_argument("--frontend", action="store_true", help="Also run frontend Vitest.")
    parser.add_argument("--list", action="store_true", help="List test groups and exit.")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without running.")
    args = parser.parse_args(raw)
    args.pytest_args = pytest_args
    return args


def list_groups() -> None:
    print("Module suites:")
    for name, tests in MODULE_SUITES.items():
        print(f"{name}: {len(tests)} tests")
        for test in tests:
            print(f"  - {test}")
    print("\nAliases:")
    for name, suites in SUITE_ALIASES.items():
        print(f"{name}: {', '.join(suites)}")
    print(f"all: {len(discover_python_tests())} tests")


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.list:
        list_groups()
        return 0

    invalid = [group for group in args.groups if group not in available_groups()]
    if invalid:
        print(f"Unknown test group(s): {', '.join(invalid)}", file=sys.stderr)
        print(f"Available groups: {', '.join(available_groups())}", file=sys.stderr)
        return 2

    missing = missing_manifest_paths()
    if missing:
        print("Missing tests referenced by TEST_GROUPS:", file=sys.stderr)
        for item in missing:
            print(f"- {item}", file=sys.stderr)
        return 2

    code = run_pytest(args.groups, args.pytest_args, args.dry_run)
    if code != 0:
        return code
    if args.frontend:
        return run_frontend(args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
