# Vision Loading State + PDF Markdown 修复实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:**
1. 在上传图片并发送时，前端 ThinkingBubble 提前展示"正在读取上传的图像..."
2. PDF 导出时将 LLM 返回的 Markdown 摘要转换为真实 HTML（加粗、标题、列表）

**Architecture:**
- Issue 1: 将 `enrich_last_user_message_with_vision` 从路由处理器移至 `event_gen()` 内部，在 vision 调用前发送 SSE thinking 事件
- Issue 2: 新增 `_markdown_to_html()` 替换现有的 `_markdownish_to_plain_paragraphs()`，在 `pdf_report.py` 中使用

**Tech Stack:** Python FastAPI, SSE, WeasyPrint, 正则表达式

---

## 文件影响

| 文件 | 改动 |
|------|------|
| `backend/routes/chat_route.py` | 重构 event_gen()，将 vision enrichment 移入生成器内 |
| `backend/report/pdf_summary.py` | 新增 `_markdown_to_html()` 函数 |
| `backend/report/pdf_report.py` | 调用 `_markdown_to_html()` 替换 `html.escape()` + replace |

---

## Task 1: 重构 chat_route.py — 将 Vision Enrichment 移入 event_gen()

**Files:**
- Modify: `backend/routes/chat_route.py:83-219`
- Test: `backend/routes/` (手动测试)

**Context:**
当前 `enrich_last_user_message_with_vision(messages, trace_id)` 在路由处理器中直接 `await`，此时 SSE 还未开始推送事件，前端收不到任何反馈。

修复方案：将 vision enrichment 移至 `event_gen()` 内部，在调用 vision LLM 前先 `yield` 一条 thinking 事件。

---

- [ ] **Step 1: 读取并确认当前 event_gen() 结构**

确认 `event_gen()` 位于 `backend/routes/chat_route.py` 第 140 行附近，参数 `messages` 从外部闭包捕获。

---

- [ ] **Step 2: 将 vision enrichment 从路由处理器移至 event_gen() 开头**

在 `event_gen()` 内部、`stream_chat()` 之前：
1. 检查 `messages[-1]["role"] == "user"` 且消息内容包含图像路径（复用 `find_image_path_in_text`）
2. 如有图像，`yield` 一条 `{"type": "thinking", "content": "正在读取上传的图像..."}` 事件
3. 执行 `messages = await enrich_last_user_message_with_vision(messages, trace_id)`
4. 闭包中的 `messages` 被更新，后续 `stream_chat()` 使用更新后的 messages

**关键约束:**
- `event_gen()` 是 async generator，`yield` 会暂停执行并发送事件
- vision enrichment 是 CPU/IO 密集的 await 调用，放在 `yield` 之后可确保前端先收到"正在识图"
- `messages` 变量需通过闭包修改（`nonlocal` 或重构为 list）

**修改后 event_gen() 开头逻辑：**
```python
async def event_gen() -> AsyncGenerator[dict, None]:
    started_at = perf_counter()
    acc: Dict[str, Any] = {"content": "", "thinking": []}
    disconnected = False

    # --- Vision enrichment with early thinking event ---
    nonlocal messages
    if messages and messages[-1].get("role") == "user":
        last_content = messages[-1].get("content") or ""
        if re.search(r"[^\s]+\.(?:png|jpg|jpeg|webp)", last_content, re.IGNORECASE):
            yield {
                "event": "message",
                "data": json.dumps(
                    {"type": "thinking", "content": "正在读取上传的图像..."},
                    ensure_ascii=False,
                ),
            }
            messages = await enrich_last_user_message_with_vision(messages, trace_id)
    # --- End vision enrichment ---

    try:
        async for event in stream_chat(
            messages,
            trace_id=trace_id,
            ...
```

同时从路由处理器（line 137）移除：
```python
# 删除这行：
messages = await enrich_last_user_message_with_vision(messages, trace_id)
```

---

- [ ] **Step 3: 添加 re import（如尚未导入）**

确认 `re` 模块已在 `backend/routes/chat_route.py` 顶部导入（第 6 行已有）。

---

- [ ] **Step 4: 手动测试验证**

1. 启动后端：`cd backend && uv run uvicorn main:app --reload --port 8001`
2. 前端发送带图像的消息
3. 浏览器 DevTools → Network → 确认 SSE 流开始前有 `{"type":"thinking","content":"正在读取上传的图像..."}`
4. 确认 ThinkingBubble 正确渲染

---

## Task 2: 新增 PDF Markdown → HTML 转换

**Files:**
- Modify: `backend/report/pdf_summary.py`
- Modify: `backend/report/pdf_report.py:49-53`
- Test: `tests/test_report_pdf.py`（如存在）

---

- [ ] **Step 1: 读取 pdf_summary.py 确认当前 _markdownish_to_plain_paragraphs 位置**

确认函数位于 `backend/report/pdf_summary.py` 第 99-103 行。

---

- [ ] **Step 2: 替换 _markdownish_to_plain_paragraphs 为 _markdown_to_html**

用以下完整实现替换第 99-103 行的函数：

```python
def _markdown_to_html(text: str) -> str:
    """将 LLM 返回的 markdown 转换为可用于 PDF 的 HTML（仅处理常用格式）。"""
    import re

    lines = text.split("\n")
    in_ul = False
    result: list[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]
        # 跳过分隔行（如 |---|）
        if re.match(r"^\|[-: |]+\|$", line) or re.match(r"^\|?\s*[-:]+\s*[-:|\s]*\|?$", line):
            i += 1
            continue
        # h2 / h3 标题
        m = re.match(r"^(#{2,3})\s+(.+)$", line)
        if m:
            if in_ul:
                result.append("</ul>")
                in_ul = False
            level = len(m.group(1))
            content = _process_inline_markdown(m.group(2))
            result.append(f"<h{level}>{content}</h{level}>")
            i += 1
            continue
        # 列表项
        m = re.match(r"^[-*]\s+(.+)$", line)
        if m:
            if not in_ul:
                result.append("<ul>")
                in_ul = True
            content = _process_inline_markdown(m.group(1))
            result.append(f"<li>{content}</li>")
            i += 1
            continue
        # 关闭未关闭的 ul
        if in_ul:
            result.append("</ul>")
            in_ul = False
        # 空行处理
        if line.strip() == "":
            i += 1
            continue
        # 普通段落
        content = _process_inline_markdown(line)
        result.append(f"<p>{content}</p>")
        i += 1

    if in_ul:
        result.append("</ul>")
    return "\n".join(result)


def _process_inline_markdown(text: str) -> str:
    """处理行内 markdown：加粗 **text** -> <strong>text</strong>"""
    import re

    # 先处理加粗
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    # 处理斜体（可选）
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    return text
```

同时将 `summarize_session_for_pdf` 中的 `_markdownish_to_plain_paragraphs(text)` 替换为 `_markdown_to_html(text)`（第 78 行）。

---

- [ ] **Step 3: 修改 pdf_report.py 使用 _markdown_to_html**

修改 `messages_to_html_document()` 函数（第 53 行附近）：

将：
```python
summary_html = html.escape(summary).replace("\n", "<br/>")
```

替换为：
```python
summary_html = _markdown_to_html(summary)
```

需要：
1. 从 `pdf_summary` 导入 `_markdown_to_html`：
   ```python
   from backend.report.pdf_summary import summarize_session_for_pdf, _markdown_to_html
   ```
2. 移除 `import html` 或保留（`html.escape` 仍用于其他字段如 title）

---

- [ ] **Step 4: 运行 backend 测试**

```bash
cd backend
PYTHONPATH=. uv run pytest tests/ -k "pdf" -v --no-header -q
```

---

## Task 3: 端到端验证

---

- [ ] **Step 1: 验证 Issue 1（Vision Loading）**

1. 前端上传一张包含表格/图表的截图
2. 发送消息
3. 观察 ThinkingBubble 是否在收到 SSE 后立即显示"正在读取上传的图像..."（在正常 thinking 步骤之前或同时出现）

---

- [ ] **Step 2: 验证 Issue 2（PDF Markdown）**

1. 进行几次有图表/KPI 的对话
2. 点击「导出 PDF 报告」
3. 打开 PDF，确认摘要部分：
   - `## 标题` 渲染为大标题（非 `##` 符号）
   - `**加粗**` 渲染为粗体（非 `**` 符号）
   - `- 列表项` 渲染为列表（非 `-` 符号）

---

## 验证检查清单

- [ ] Issue 1: ThinkingBubble 在 vision 处理期间显示"正在读取上传的图像..."
- [ ] Issue 1: vision 处理完成后正常生成回复，两阶段（vision + 回复）都正常
- [ ] Issue 2: PDF 摘要中加粗文字显示为粗体
- [ ] Issue 2: PDF 摘要中标题显示为大标题（非 Markdown 符号）
- [ ] Issue 2: PDF 摘要中列表显示为列表（非 Markdown 符号）
