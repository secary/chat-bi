---
name: chatbi-semantic-query
description: Use when Codex or another agent needs to answer Chinese natural-language data questions against the local ChatBI demo MySQL database, map business terms to governed metrics and dimensions, generate safe read-only SQL, execute metric queries, or return JSON/table results for sales, revenue, gross margin, target achievement, customer, retention, region, channel, product, and monthly trend analysis.
---

# ChatBI Semantic Query

Use this skill to query the local ChatBI demo database from Chinese business language.

## Workflow

1. Use `scripts/chatbi_semantic_query.py` for natural-language metric questions.
2. Prefer the script over manually writing SQL when the user asks about governed metrics, dimensions, aliases, trends, rankings, or filters.
3. Run with `--show-sql` when the generated SQL should be inspected or explained.
4. Run with `--json` when another script, report generator, dashboard builder, or agent needs structured output.
5. Explain results in business language after execution. Include the important numbers and the metric meaning when useful.

## Common Commands

```bash
python3 scripts/chatbi_semantic_query.py "按区域看2026年1月到4月销售额排行" --show-sql
python3 scripts/chatbi_semantic_query.py "2026年4月华东目标完成率是多少" --show-sql
python3 scripts/chatbi_semantic_query.py "按月看客户留存率趋势" --json
python3 scripts/chatbi_semantic_query.py "线上渠道软件服务销售额是多少" --show-sql
```

Run commands from this skill directory, or pass the full path to the bundled script.

## Supported Semantics

- Metrics come from `metric_definition`.
- Aliases come from `alias_mapping`, such as `收入` to `销售额`.
- Dimensions include `区域`, `月份`, `时间`, `部门`, `产品类别`, `产品名称`, `渠道`, and `客户类型`; `时间` defaults to monthly grouping.
- Dimension synonyms are supported for common business phrasing, such as `大区/地区/片区` to `区域`, `业务线/品类/产品类型` to `产品类别`, `成交来源/获客渠道/销售渠道` to `渠道`, and `客群/客户分层/客户类别` to `客户类型`.
- Filters are inferred from enum values in the source table, such as `华东`, `线上`, `软件服务`, and `企业客户`.
- Time expressions include `2026年4月`, `2026年1月到4月`, `2026年1-4月`, and `2026年`.
- Ranking expressions include `排行`, `排名`, `最高`, `最低`, `top N`, and `前 N`.

## Database Defaults

The bundled script defaults to:

- Host: `127.0.0.1`
- Port: `3307`
- Database: `chatbi_demo`
- User: `demo_user`
- Password: `demo_pass`

Override with environment variables:

- `CHATBI_DB_HOST`
- `CHATBI_DB_PORT`
- `CHATBI_DB_USER`
- `CHATBI_DB_PASSWORD`
- `CHATBI_DB_NAME`

## Safety

Use this skill for read-only semantic queries. The script should generate `SELECT` queries from governed metadata and whitelist-like table/field handling. Do not execute destructive SQL. Do not bypass the semantic query script unless the user explicitly asks for raw SQL investigation.

If the database is running in Docker and local MySQL access is blocked by the sandbox, request permission to run the script with elevated local network access.
