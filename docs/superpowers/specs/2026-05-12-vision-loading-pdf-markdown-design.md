# 设计方案：图像处理加载状态 + PDF Markdown 渲染

## Context

1. **问题1：图像处理时无加载提示**
   - 用户上传图像后，后端 `enrich_last_user_message_with_vision()` 同步调用 vision LLM 进行表格/图表提取
   - 这个过程发生在 SSE 流开始**之前**，前端收不到任何事件
   - 用户看到"发送成功"后系统就卡住，没有反馈

2. **问题2：PDF 导出显示原始 Markdown 符号**
   - `summarize_session_for_pdf()` 调用 LLM 生成 Markdown 格式摘要
   - `_markdownish_to_plain_paragraphs()` 仅去除 `#` 标题标记
   - `**bold**`、`- list`、`## heading` 等符号未经转换直接写入 HTML
   - WeasyPrint 将其作为普通文本渲染，PDF 中显示原始 Markdown 符号

## 解决方案

### Issue 1: Vision 处理时展示 Thinking 气泡

**方案**: 后端在调用 vision LLM **之前**，通过 SSE 发送一条 `thinking` 事件。

#### 实现位置
- `backend/routes/chat_route.py` 的 `/chat` 端点

#### 修改逻辑
```python
# 检测到用户消息包含图像路径时，
# 先发送一条 thinking 事件，再调用 vision LLM
if find_image_path_in_text(message_content):
    # 通过现有 streamer 发送 thinking 事件
    await websocket.send_json({
        "type": "thinking",
        "content": "正在读取上传的图像..."
    })
    # 然后执行 vision  enrichment...
```

前端 `useChat.ts` 会将这条 thinking 追加到 `thinking[]`，ThinkingBubble 自然展示"正在读取上传的图像..."。

#### 关键文件
- `backend/routes/chat_route.py` - 发送 vision 预处理 thinking 事件
- `frontend/src/hooks/useChat.ts` - 无需修改，已处理 `thinking` 事件类型

---

### Issue 2: PDF 导出时将 Markdown 转换为 HTML

**方案**: 在 `pdf_summary.py` 的 `_markdownish_to_plain_paragraphs()` 中实现完整的 Markdown 转 HTML 逻辑。

#### 实现位置
- `backend/report/pdf_summary.py`

#### 转换规则
| Markdown | HTML |
|----------|------|
| `## heading` | `<h2>heading</h2>` |
| `### heading` | `<h3>heading</h3>` |
| `**bold**` | `<strong>bold</strong>` |
| `- item` / `* item` | `<li>item</li>` (组合为 `<ul>`) |
| `\n\n` | `<br/>` (段落分隔) |

#### 代码逻辑
```python
def _markdown_to_html(text: str) -> str:
    """将 LLM 返回的 markdown 转换为可用于 PDF 的 HTML。"""
    lines = text.split('\n')
    in_ul = False
    result = []
    for line in lines:
        # 标题
        if re.match(r'^#{2,3}\s+(.+)$', line):
            if in_ul:
                result.append('</ul>')
                in_ul = False
            m = re.match(r'^(#{2,3})\s+(.+)$', line)
            level = len(m.group(1))
            result.append(f'<h{level}>{m.group(2)}</h{level}>')
        # 列表项
        elif re.match(r'^[-*]\s+(.+)$', line):
            if not in_ul:
                result.append('<ul>')
                in_ul = True
            m = re.match(r'^[-*]\s+(.+)$', line)
            result.append(f'<li>{m.group(1)}</li>')
        else:
            if in_ul:
                result.append('</ul>')
                in_ul = False
            if line.strip():
                # 处理行内加粗
                processed = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line)
                result.append(f'<p>{processed}</p>')
    if in_ul:
        result.append('</ul>')
    return '\n'.join(result)
```

然后在 `pdf_report.py` 的 `messages_to_html_document()` 中，不再用 `html.escape(summary).replace("\n", "<br/>")`，而是直接使用 `_markdown_to_html(summary)`。

#### 关键文件
- `backend/report/pdf_summary.py` - 新增 `_markdown_to_html()` 函数
- `backend/report/pdf_report.py` - 调用 `_markdown_to_html()` 而非 `html.escape()`

---

## 验证方法

### Issue 1
1. 上传一张包含表格/图表的截图
2. 发送消息给 ChatBI
3. 观察 ThinkingBubble 是否在 SSE 开始前就显示"正在读取上传的图像..."

### Issue 2
1. 进行几次对话，产生一些数据
2. 点击「导出 PDF 报告」
3. 打开 PDF，确认摘要部分的加粗、标题、列表都正确渲染，而非显示 `**`、`#`、`-` 等原始符号

## 风险与约束

- Issue 1: 需要确保 `websocket.send_json` 在 vision enrichment 之前被调用，且不阻塞后续处理
- Issue 2: Markdown 到 HTML 的转换是手写的简化版，仅覆盖 LLM 常用输出格式（`##`、`**`、`-`/`*`），不处理表格、代码块等复杂格式
