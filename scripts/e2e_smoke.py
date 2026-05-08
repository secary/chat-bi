#!/usr/bin/env python3
"""
ChatBI E2E smoke test — 需要后端运行中。

用法：
  python scripts/e2e_smoke.py                          # 默认 http://localhost:8001
  python scripts/e2e_smoke.py --url http://localhost:8000
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
from dataclasses import dataclass, field

# ── ANSI ─────────────────────────────────────────────────────────────────────
USE_COLOR = sys.stdout.isatty() and os.getenv("NO_COLOR") is None
GREEN = "\033[32m" if USE_COLOR else ""
RED = "\033[31m" if USE_COLOR else ""
GRAY = "\033[90m" if USE_COLOR else ""
BOLD = "\033[1m" if USE_COLOR else ""
RESET = "\033[0m" if USE_COLOR else ""

# ── 测试用例定义 ──────────────────────────────────────────────────────────────


@dataclass
class Case:
    id: str
    label: str
    message: str
    expect_skills: list[str] = field(default_factory=list)  # thinking 中必须出现的 skill
    no_skill_call: bool = False  # thinking 中不应出现任何 Skill 调用
    expect_text: list[str] = field(default_factory=list)  # text 事件中必须出现的字符串
    expect_no_text: list[str] = field(default_factory=list)  # text 事件中不应出现的字符串
    expect_chart: bool = False  # 必须有 chart 事件
    multi_agents: bool = False


CASES: list[Case] = [
    # ── 单 Skill ──────────────────────────────────────────────────────────────
    Case(
        "S1",
        "区域销售额排行",
        "1-4月各区域销售额排行",
        expect_skills=["chatbi-semantic-query"],
        expect_chart=True,
    ),
    Case(
        "S2",
        "按月趋势",
        "2026年销售额按月趋势",
        expect_skills=["chatbi-semantic-query"],
        expect_chart=True,
    ),
    Case("S3", "单值 KPI", "华东4月毛利率", expect_skills=["chatbi-semantic-query"]),
    Case(
        "S4", "数据库概览", "当前数据库有哪些表可以查", expect_skills=["chatbi-database-overview"]
    ),
    Case("S5", "环比对比", "销售额和上月相比怎么样", expect_skills=["chatbi-comparison"]),
    Case(
        "S6",
        "指标口径解释",
        "销售额口径是什么",
        expect_skills=["chatbi-metric-explainer"],
        expect_text=["销售额口径"],
    ),
    # ── 多步 Skill ────────────────────────────────────────────────────────────
    Case(
        "M1",
        "查询+建议（区域）",
        "1-4月各区域销售额排行，并给出经营建议",
        expect_skills=["chatbi-semantic-query", "chatbi-decision-advisor"],
        expect_text=["决策"],
    ),
    Case(
        "M2",
        "查询+建议（毛利率）",
        "各渠道毛利率经营建议",
        expect_skills=["chatbi-semantic-query", "chatbi-decision-advisor"],
        expect_text=["决策"],
    ),
    Case(
        "M3",
        "查询+建议（区域焦点）",
        "华东销售额建议",
        expect_skills=["chatbi-semantic-query", "chatbi-decision-advisor"],
        expect_text=["决策"],
    ),
    # ── 图表渲染修复 ──────────────────────────────────────────────────────────
    Case(
        "C1",
        "图表无原始 JSON",
        "请把下面结果用最合适的图表可视化出来："
        '{"question":"2026年1-4月销售额趋势","rows":['
        '{"月份":"2026-01","销售额":355000},'
        '{"月份":"2026-02","销售额":378000},'
        '{"月份":"2026-03","销售额":412000},'
        '{"月份":"2026-04","销售额":462000}]}',
        expect_no_text=['"series":', '"xAxis":'],
        expect_chart=True,
    ),
    # ── 边界场景 ──────────────────────────────────────────────────────────────
    Case("E1", "小聊天不调 Skill", "你好", no_skill_call=True),
    Case("E2", "不存在年份", "2024年销售额", expect_skills=["chatbi-semantic-query"]),
]

# ── SSE 读取 ──────────────────────────────────────────────────────────────────


def _stream_events(url: str, message: str, token: str | None, multi_agents: bool, timeout: int):
    payload = json.dumps(
        {
            "message": message,
            "history": [],
            "multi_agents": multi_agents,
        }
    ).encode()
    headers = {
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    if token:
        headers["Authorization"] = token

    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        for raw in resp:
            line = raw.decode("utf-8", errors="replace").rstrip("\n\r")
            if not line.startswith("data:"):
                continue
            try:
                yield json.loads(line[5:].strip())
            except json.JSONDecodeError:
                pass


# ── 断言 ──────────────────────────────────────────────────────────────────────


def _run_case(case: Case, base_url: str, token: str | None, timeout: int):
    url = base_url.rstrip("/") + "/chat"
    thinking_text = ""
    all_text = ""
    has_chart = False
    got_done = False
    errors: list[str] = []

    try:
        for event in _stream_events(url, case.message, token, case.multi_agents, timeout):
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

    # 断言有图表
    if case.expect_chart and not has_chart:
        errors.append("期望有 chart 事件，但未收到")

    return len(errors) == 0, errors


# ── 主入口 ────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="ChatBI E2E smoke test")
    parser.add_argument("--url", default=os.getenv("CHATBI_E2E_URL", "http://localhost:8001"))
    parser.add_argument(
        "--token",
        default=os.getenv("CHATBI_E2E_TOKEN"),
        help='如开启鉴权，传 "Bearer xxx"；也可用 CHATBI_E2E_TOKEN',
    )
    parser.add_argument("--cases", default=None, help="逗号分隔的用例 ID，如 S1,M1,C1")
    parser.add_argument("--timeout", type=int, default=120, help="每条用例超时秒数")
    args = parser.parse_args()

    filter_ids = (
        {item.strip() for item in args.cases.split(",") if item.strip()} if args.cases else None
    )
    known_ids = {case.id for case in CASES}
    unknown_ids = sorted(filter_ids - known_ids) if filter_ids else []
    if unknown_ids:
        print(f"{RED}未知用例 ID：{', '.join(unknown_ids)}{RESET}")
        print(f"可用用例：{', '.join(sorted(known_ids))}")
        sys.exit(2)

    cases = [c for c in CASES if filter_ids is None or c.id in filter_ids]

    print(f"\n{BOLD}ChatBI E2E Smoke Test{RESET}  →  {args.url}")
    print(f"共 {len(cases)} 条用例，超时 {args.timeout}s/条\n")

    passed = failed = 0
    for case in cases:
        print(f"  {GRAY}[{case.id}]{RESET} {case.label} ", end="", flush=True)
        t0 = time.time()
        ok, errors = _run_case(case, args.url, args.token, args.timeout)
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
