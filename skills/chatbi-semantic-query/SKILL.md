---
name: chatbi-semantic-query
description: Use when Codex or another agent needs to answer Chinese natural-language data questions against the local ChatBI demo MySQL database, map business terms to governed metrics and dimensions, generate safe read-only SQL, execute metric queries, or return JSON/table results for sales, revenue, gross margin, target achievement, customer, retention, region, channel, product, and monthly trend analysis.
---

# ChatBI Semantic Query

Use this skill to query the local ChatBI demo database from Chinese business language, including short and incomplete natural-language metric requests.

## Workflow

1. Use `scripts/chatbi_semantic_query.py` for natural-language metric questions.
2. Prefer the script over manually writing SQL when the user asks about governed metrics, dimensions, aliases, trends, rankings, or filters.
3. Trigger this skill for terse requests such as `1-4月销售额排行`, `各区域销售额`, `华东4月毛利率`, or `线上软件服务收入`.
4. Pass the user's original natural-language question as the first script argument. Do not rewrite missing years or dimensions in the prompt.
5. Run with `--show-sql` when the generated SQL should be inspected or explained.
6. Run with `--json` when another script, report generator, dashboard builder, or agent needs structured output.
7. Run with `--chart-html <path>` when the user wants a quick chart from the query result.
8. Explain results in business language after execution. Include the important numbers and the metric meaning when useful.

## Common Commands

```bash
python3 scripts/chatbi_semantic_query.py "1-4月销售额排行" --show-sql
python3 scripts/chatbi_semantic_query.py "各区域销售额" --show-sql
python3 scripts/chatbi_semantic_query.py "按区域看2026年1月到4月销售额排行" --show-sql
python3 scripts/chatbi_semantic_query.py "2026年4月华东目标完成率是多少" --show-sql
python3 scripts/chatbi_semantic_query.py "按月看客户留存率趋势" --json
python3 scripts/chatbi_semantic_query.py "线上渠道软件服务销售额是多少" --show-sql
python3 scripts/chatbi_semantic_query.py "按区域看2026年1月到4月销售额排行" --chart-html /tmp/chatbi-region-sales.html
python3 scripts/chatbi_semantic_query.py "按月看客户留存率趋势" --chart-html /tmp/chatbi-retention-trend.html
```

Run commands from this skill directory, or pass the full path to the bundled script.

## Supported Semantics

- Metrics come from `metric_definition`.
- Aliases come from `alias_mapping`, such as `收入` to `销售额`.
- Dimensions include `区域`, `月份`, `时间`, `部门`, `产品类别`, `产品名称`, `渠道`, and `客户类型`; `时间` defaults to monthly grouping.
- Dimension synonyms are supported for common business phrasing, such as `大区/地区/片区` to `区域`, `业务线/品类/产品类型` to `产品类别`, `成交来源/获客渠道/销售渠道` to `渠道`, and `客群/客户分层/客户类别` to `客户类型`.
- Filters are inferred from enum values in the source table, such as `华东`, `线上`, `软件服务`, and `企业客户`.
- Time expressions include `2026年4月`, `2026年1月到4月`, `2026年1-4月`, `1-4月`, `1月到4月`, and `2026年`.
- Month ranges without a year use the latest year in the selected fact table; the demo data currently resolves `1-4月` to 2026年1-4月.
- Ranking expressions include `排行`, `排名`, `最高`, `最低`, `top N`, and `前 N`; ranking without an explicit dimension defaults to `区域` when the metric supports it.
- Chart output uses standalone HTML + SVG. Monthly results use a line chart; other grouped results use a bar chart.

## Visualization Guidance

When returning structured results for a UI, include or recommend a chart plan alongside the business explanation. Pick the default chart from the user's intent and result shape, not from the skill name alone.

- Use a bar chart for categorical comparisons, rankings, highest/lowest questions, and region/channel/product/department breakdowns.
- Use a line chart for monthly or time trend questions, especially when the result has `月份`, `时间`, or `month`.
- Use a pie chart for composition, share, proportion, or contribution questions where categories sum to a meaningful whole.
- Use KPI cards for single-scope metric summaries, such as one region's sales, target achievement, gross margin, or retention.
- Highlight the best or worst category when the user asks for `最高`, `最低`, `最好`, `最差`, ranking, or anomaly detection.
- Prefer interactive ECharts options with tooltip, legend filtering, click highlight, and dataZoom for time series.

Suggested chart plan shape for downstream renderers:

```json
{
  "chart_type": "bar|line|pie|kpi_cards",
  "dimension": "区域",
  "metrics": ["销售额"],
  "highlight": {"mode": "min|max", "field": "销售额"},
  "interactions": {
    "tooltip": true,
    "legend_filter": true,
    "data_zoom": false,
    "click_highlight": true
  }
}
```

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
