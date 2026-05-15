---
name: chatbi-database-overview
description: Use when Codex or another agent needs to summarize the currently connected ChatBI business database, list queryable tables or views, explain what each table contains, show row counts, fields, semantic metrics, dimensions, aliases, or answer questions like 当前数据库有哪些表可以查, 数据库概览, 业务库结构, 表清单, schema 概述.
trigger_conditions:
  - 用户问有哪些表、库概览、schema、可查数据清单
  - 取数前需要了解演示库资产
when_not_to_use:
  - 用户要具体指标数值（用 chatbi-semantic-query）
  - 用户在上传文件上分析（非本技能职责）
required_context:
  - 演示业务库可连接
---

# ChatBI Database Overview

Use this skill when the user asks what data assets are available before asking a metric question.

## Workflow

1. Run `scripts/database_overview.py` against the active business database.
2. The script reads `information_schema` plus ChatBI semantic metadata tables when present.
3. Return the table inventory and recommended next questions directly.
4. If the user asks for actual metric values afterward, switch to `chatbi-semantic-query`.

## Commands

```bash
python3 scripts/database_overview.py --json
python3 scripts/database_overview.py
python3 scripts/database_overview.py --include-columns 8 --json
```

Run commands from this skill directory, or pass the full path to the bundled script.

## Coverage

- Queryable assets include base tables and views in the active database.
- Semantic tables are separated from business query assets.
- For each business asset, the script returns table type, row count, field names, field types, and available business field descriptions.
- When metadata exists, the script also returns governed metrics, dimensions, and alias count.

## Presentation Guidance

Return a concise inventory first: how many business tables/views can be queried, what they are, and typical questions the user can ask next.

## Safety

This skill is read-only. It only uses `SELECT`, `SHOW`, and `information_schema` queries. Do not modify data or metadata.
