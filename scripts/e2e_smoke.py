#!/usr/bin/env python3
"""
ChatBI E2E smoke test — 需要后端运行中。

用法：
  python scripts/e2e_smoke.py                          # 默认 http://localhost:8226
  python scripts/e2e_smoke.py --url http://localhost:8226
  python scripts/e2e_smoke.py --token "Bearer xxx"    # 开启鉴权时传 token
  python scripts/e2e_smoke.py --cases S1,M1,C1        # 只跑指定用例
  python scripts/e2e_smoke.py --timeout 90            # 每条用例超时秒数（默认 120）
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import time
import urllib.error
import urllib.request

try:
    from scripts.e2e_cases import CASES, CASE_GROUPS, Case
    from scripts.e2e_runner import run_step_case, stream_chat_events
except ModuleNotFoundError:
    from e2e_cases import CASES, CASE_GROUPS, Case
    from e2e_runner import run_step_case, stream_chat_events

# ── ANSI ─────────────────────────────────────────────────────────────────────
USE_COLOR = sys.stdout.isatty() and os.getenv("NO_COLOR") is None
GREEN = "\033[32m" if USE_COLOR else ""
RED = "\033[31m" if USE_COLOR else ""
GRAY = "\033[90m" if USE_COLOR else ""
BOLD = "\033[1m" if USE_COLOR else ""
RESET = "\033[0m" if USE_COLOR else ""


def _login_token(base_url: str, username: str, password: str, timeout: int) -> str:
    url = base_url.rstrip("/") + "/auth/login"
    payload = json.dumps({"username": username, "password": password}).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    token = str(data.get("access_token") or "")
    token_type = str(data.get("token_type") or "bearer")
    if not token:
        raise RuntimeError("登录响应缺少 access_token")
    return f"{token_type.capitalize()} {token}"


def _resolve_token(args: argparse.Namespace) -> str | None:
    if args.token:
        return args.token if args.token.lower().startswith("bearer ") else f"Bearer {args.token}"
    if not args.username and not args.password:
        return None
    if not args.username or not args.password:
        raise RuntimeError("自动登录需要同时提供 username 和 password")
    return _login_token(args.url, args.username, args.password, args.timeout)


# ── SSE 读取 ──────────────────────────────────────────────────────────────────


def _stream_events(url: str, message: str, token: str | None, timeout: int):
    yield from stream_chat_events(url, message, token, timeout)


# ── 断言 ──────────────────────────────────────────────────────────────────────


def _run_case(case: Case, base_url: str, token: str | None, timeout: int):
    if case.steps:
        return run_step_case(case, base_url, token, timeout)
    url = base_url.rstrip("/") + "/chat"
    thinking_text = ""
    all_text = ""
    has_chart = False
    got_done = False
    errors: list[str] = []

    try:
        for event in _stream_events(url, case.message, token, timeout):
            t = event.get("type", "")
            content = event.get("content", "")
            if t == "thinking" and isinstance(content, str):
                thinking_text += content + "\n"
            elif t == "text":
                all_text += (
                    content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
                )
            elif t == "chart":
                has_chart = True
            elif t == "error":
                errors.append(f"SSE error：{content}")
            elif t == "done":
                got_done = True
                break
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:300]
        return False, [f"HTTP {e.code}：{detail or e.reason}"]
    except urllib.error.URLError as e:
        return False, [f"连接失败：{e}"]
    except (TimeoutError, socket.timeout):
        return False, [f"超时（>{timeout}s）"]

    if not got_done:
        errors.append("未收到 done 事件")

    # 断言 skill 出现
    for skill in case.expect_skills:
        if f"「{skill}」" not in thinking_text:
            errors.append(f"thinking 中未出现 Skill「{skill}」")

    # 断言无 skill 调用
    if case.no_skill_call and "Skill「" in thinking_text:
        errors.append("期望无 Skill 调用，但 thinking 中出现了 Skill 调用")

    # 断言 text 中不含特定字符串
    for s in case.expect_text:
        if s not in all_text:
            errors.append(f"text 事件中应出现 {s!r}")

    for s in case.expect_no_text:
        if s in all_text:
            errors.append(f"text 事件中不应出现 {s!r}")

    if case.expect_chart and not has_chart:
        errors.append("期望有 chart 事件，但未收到")

    return len(errors) == 0, errors


def _split_ids(raw: str | None) -> set[str] | None:
    return {item.strip() for item in raw.split(",") if item.strip()} if raw else None


def _selected_cases(
    case_ids: set[str] | None, group_ids: set[str] | None
) -> tuple[list[Case], list[str]]:
    known_ids = {case.id for case in CASES}
    selected_ids = case_ids
    unknown = sorted(case_ids - known_ids) if case_ids else []
    if selected_ids is None and group_ids:
        unknown.extend(sorted(group_ids - set(CASE_GROUPS)))
        selected_ids = {
            case_id for group in group_ids & set(CASE_GROUPS) for case_id in CASE_GROUPS[group]
        }
    return [case for case in CASES if selected_ids is None or case.id in selected_ids], unknown


# ── 主入口 ────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="ChatBI E2E smoke test")
    parser.add_argument("--url", default=os.getenv("CHATBI_E2E_URL", "http://localhost:8226"))
    parser.add_argument(
        "--token",
        default=os.getenv("CHATBI_E2E_TOKEN"),
        help='如开启鉴权，传 "Bearer xxx" 或裸 token；也可用 CHATBI_E2E_TOKEN',
    )
    parser.add_argument("--username", default=os.getenv("CHATBI_E2E_USERNAME"))
    parser.add_argument("--password", default=os.getenv("CHATBI_E2E_PASSWORD"))
    parser.add_argument("--cases", default=None, help="逗号分隔的用例 ID，如 S1,M1,C1")
    parser.add_argument(
        "--groups",
        default=os.getenv("CHATBI_E2E_GROUPS"),
        help=f"逗号分隔的功能组：{', '.join(sorted(CASE_GROUPS))}",
    )
    parser.add_argument("--timeout", type=int, default=120, help="每条用例超时秒数")
    args = parser.parse_args()

    try:
        token = _resolve_token(args)
    except (RuntimeError, urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        print(f"{RED}E2E 登录失败：{e}{RESET}")
        sys.exit(1)

    filter_ids = _split_ids(args.cases)
    group_ids = _split_ids(args.groups)
    cases, unknown_ids = _selected_cases(filter_ids, group_ids)
    if unknown_ids:
        print(f"{RED}未知用例 ID：{', '.join(unknown_ids)}{RESET}")
        known_ids = {case.id for case in CASES}
        print(f"可用用例：{', '.join(sorted(known_ids))}")
        print(f"可用功能组：{', '.join(sorted(CASE_GROUPS))}")
        sys.exit(2)

    print(f"\n{BOLD}ChatBI E2E Smoke Test{RESET}  →  {args.url}")
    print(f"共 {len(cases)} 条用例，超时 {args.timeout}s/条\n")

    passed = failed = 0
    for case in cases:
        print(f"  {GRAY}[{case.id}]{RESET} {case.label} ", end="", flush=True)
        t0 = time.time()
        ok, errors = _run_case(case, args.url, token, args.timeout)
        elapsed = time.time() - t0

        if ok:
            print(f"{GREEN}✓{RESET}  {GRAY}{elapsed:.1f}s{RESET}")
            passed += 1
        else:
            print(f"{RED}✗{RESET}  {GRAY}{elapsed:.1f}s{RESET}")
            for e in errors:
                print(f"      {RED}→ {e}{RESET}")
            failed += 1

    total = passed + failed
    status = f"{GREEN}全部通过{RESET}" if failed == 0 else f"{RED}{failed} 条失败{RESET}"
    print(f"\n{BOLD}结果：{passed}/{total} 通过  {status}{RESET}\n")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
