from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.request
from pathlib import Path

try:
    from scripts.e2e_cases import Case, CaseStep
except ModuleNotFoundError:
    from e2e_cases import Case, CaseStep

ROOT = Path(__file__).resolve().parents[1]


def stream_chat_events(
    url: str,
    message: str,
    token: str | None,
    timeout: int,
    history: list[dict] | None = None,
    uploads: list[dict] | None = None,
):
    payload = json.dumps(
        {
            "message": message,
            "history": history or [],
            "uploads": uploads or [],
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


def upload_file(base_url: str, path: str, token: str | None, timeout: int) -> dict:
    file_path = (ROOT / path).resolve()
    boundary = f"----chatbi-e2e-{int(time.time() * 1000)}"
    head = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{file_path.name}"\r\n'
        "Content-Type: text/csv\r\n\r\n"
    ).encode()
    body = head + file_path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    if token:
        headers["Authorization"] = token
    req = urllib.request.Request(
        base_url.rstrip("/") + "/upload", data=body, headers=headers, method="POST"
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def upload_context_message(message: str, uploads: list[dict]) -> str:
    if not uploads:
        return message
    lines = [
        "[ChatBI 附件上下文：用户已上传以下附件。若当前问题涉及附件内容，必须优先使用这些路径处理；不要把路径暴露给用户。]"
    ]
    for item in uploads:
        server_path = str(item.get("server_path") or "").strip()
        if not server_path:
            continue
        filename = str(item.get("filename") or Path(server_path).name)
        lines.append(
            f"- 数据文件：{filename}；路径：{server_path}；如问题涉及文件，先校验结构；"
            "符合现有业务表就直接分析，不符合就按通用表分析。"
        )
    return "\n".join(lines) + "\n\n" + message if len(lines) > 1 else message


def assert_step(
    step: CaseStep,
    thinking_text: str,
    all_text: str,
    has_chart: bool,
    has_proposal: bool,
    has_dashboard: bool,
    got_done: bool,
    errors: list[str],
) -> None:
    if not got_done:
        errors.append("未收到 done 事件")
    for skill in step.expect_skills:
        if f"「{skill}」" not in thinking_text:
            errors.append(f"thinking 中未出现 Skill「{skill}」")
    if step.no_skill_call and "Skill「" in thinking_text:
        errors.append("期望无 Skill 调用，但 thinking 中出现了 Skill 调用")
    for s in step.expect_text:
        if s not in all_text:
            errors.append(f"text 事件中应出现 {s!r}")
    for s in step.expect_no_text:
        if s in all_text:
            errors.append(f"text 事件中不应出现 {s!r}")
    if step.expect_chart and not has_chart:
        errors.append("期望有 chart 事件，但未收到")
    if step.expect_analysis_proposal and not has_proposal:
        errors.append("期望有 analysis_proposal 事件，但未收到")
    if step.expect_dashboard_ready and not (has_dashboard or has_chart):
        errors.append("期望有 dashboard_ready 或 chart 事件，但未收到")


def collect_chat(
    base_url: str,
    message: str,
    token: str | None,
    timeout: int,
    history: list[dict] | None = None,
    uploads: list[dict] | None = None,
) -> tuple[dict, list[str]]:
    url = base_url.rstrip("/") + "/chat"
    out = {"thinking": "", "text": "", "chart": False, "proposal": None, "dashboard": False}
    errors: list[str] = []
    got_done = False
    try:
        for event in stream_chat_events(url, message, token, timeout, history, uploads):
            t = event.get("type", "")
            content = event.get("content", "")
            if t == "thinking":
                out["thinking"] += content if isinstance(content, str) else json.dumps(content)
                out["thinking"] += "\n"
            elif t == "text":
                out["text"] += content if isinstance(content, str) else json.dumps(content)
            elif t == "chart":
                out["chart"] = True
            elif t == "analysis_proposal":
                out["proposal"] = content
            elif t == "dashboard_ready":
                out["dashboard"] = True
            elif t == "error":
                errors.append(f"SSE error：{content}")
            elif t == "done":
                got_done = True
                break
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:300]
        return out, [f"HTTP {e.code}：{detail or e.reason}"]
    except urllib.error.URLError as e:
        return out, [f"连接失败：{e}"]
    except (TimeoutError, socket.timeout):
        return out, [f"超时（>{timeout}s）"]
    out["done"] = got_done
    return out, errors


def run_step_case(case: Case, base_url: str, token: str | None, timeout: int):
    errors: list[str] = []
    uploads = [upload_file(base_url, case.upload_file, token, timeout)] if case.upload_file else []
    history: list[dict] = []
    for step in case.steps:
        out, step_errors = collect_chat(base_url, step.message, token, timeout, history, uploads)
        errors.extend(step_errors)
        assert_step(
            step,
            str(out["thinking"]),
            str(out["text"]),
            bool(out["chart"]),
            out["proposal"] is not None,
            bool(out["dashboard"]),
            bool(out.get("done")),
            errors,
        )
        history.append({"role": "user", "content": upload_context_message(step.message, uploads)})
        assistant = {"role": "assistant", "content": str(out["text"])}
        if out["proposal"] is not None:
            assistant["analysisProposal"] = out["proposal"]
        history.append(assistant)
        uploads = []
    return len(errors) == 0, errors
