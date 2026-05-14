---
name: chatbi-auto-analysis
description: Auto-analysis middleware for uploaded tables. It profiles table rows, proposes metrics for user confirmation, executes accepted metrics with deterministic calculations, and emits frontend-ready analysis proposal/dashboard JSON for charts and dashboards.
---

## Workflow

Use this skill after `chatbi-file-ingestion` has read an uploaded CSV/XLSX and returned rows.

1. Profile the uploaded rows: columns, semantic roles, time/numeric/category/id fields.
2. Propose analysis metrics as frontend-renderable JSON plus Markdown.
3. Ask the user to confirm selected metric IDs before execution when the request is exploratory.
4. After confirmation, execute only supported metric plans with deterministic code.
5. Return `charts`, `kpis`, and `dashboard_middleware` so the frontend can render a full uploaded-file dashboard.

## Commands

```bash
PYTHONPATH=. .venv/bin/python skills/chatbi-auto-analysis/scripts/auto_analysis.py '{"question":"生成上传文件看板","rows":[...]}' --json
PYTHONPATH=. .venv/bin/python skills/chatbi-auto-analysis/scripts/auto_analysis.py '{"question":"采纳全部指标","mode":"execute","rows":[...]}' --json
```

## Safety

- Do not execute arbitrary Python, SQL, or formula text from an LLM.
- LLM planning may suggest metric candidates, but execution must validate field names and use whitelisted formulas.
- If required fields are missing or ambiguous, return `need_confirmation` or `need_clarification` with Markdown guidance.
