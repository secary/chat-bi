---
name: chatbi-semantic-query
description: Use when Codex or another agent needs to answer Chinese natural-language data questions against the local ChatBI demo MySQL database, map business terms to governed metrics and dimensions, generate safe read-only SQL, execute metric queries, or return JSON/table results for sales, revenue, gross margin, target achievement, customer, retention, region, channel, product, and monthly trend analysis.
trigger_conditions:
  - 用户用中文问演示库业务指标、排行、趋势、汇总或具体数值
  - 短句问数如「1-4月销售额排行」「各区域销售额」
  - 用户明确查询演示业务库且与上传文件无关
when_not_to_use:
  - 对话含本地上传路径（chatbi-uploads、/tmp/ 下 csv/xlsx）
  - 用户只问库表清单或 schema（用 chatbi-database-overview）
  - 用户问环比/比上月（用 chatbi-comparison）
  - 用户只要指标口径不要数值（用 chatbi-metric-explainer）
required_context:
  - 演示库可连接；首参优先保留用户原问句
validator_requires:
  - no_upload_path_in_thread
---

# ChatBI Semantic Query

Use this skill to query the local ChatBI demo database from Chinese business language, including short and incomplete natural-language metric requests.

## Workflow

1. Use `scripts/chatbi_semantic_query.py` for natural-language metric questions.
2. Prefer the script over manually writing SQL when the user asks about governed metrics, dimensions, aliases, trends, rankings, or filters.
3. Trigger this skill for terse requests such as `1-4月销售额排行`, `各区域销售额`, `某区域单月毛利率`, or `某渠道某产品销售额`.
4. Pass the user's original natural-language question as the first script argument. Do not rewrite missing years or dimensions in the prompt.
5. Run with `--show-sql` when the generated SQL should be inspected or explained.
6. Run with `--json` for structured output. Agent execution already appends `--json` automatically, so only add it explicitly for manual CLI use.
7. Run with `--chart-html <path>` when the user wants a quick standalone preview chart from the query result.
8. Explain results in business language after execution. Include the important numbers and the metric meaning when useful.

## Common Commands

```bash
PYTHONPATH=. .venv/bin/python skills/chatbi-semantic-query/scripts/chatbi_semantic_query.py "1-4月销售额排行" --show-sql
PYTHONPATH=. .venv/bin/python skills/chatbi-semantic-query/scripts/chatbi_semantic_query.py "各区域销售额" --show-sql
PYTHONPATH=. .venv/bin/python skills/chatbi-semantic-query/scripts/chatbi_semantic_query.py "按区域看1月到4月销售额排行" --show-sql
PYTHONPATH=. .venv/bin/python skills/chatbi-semantic-query/scripts/chatbi_semantic_query.py "华东4月目标完成率是多少" --show-sql
PYTHONPATH=. .venv/bin/python skills/chatbi-semantic-query/scripts/chatbi_semantic_query.py "按月看客户留存率趋势" --json
PYTHONPATH=. .venv/bin/python skills/chatbi-semantic-query/scripts/chatbi_semantic_query.py "线上渠道软件服务销售额是多少" --show-sql
PYTHONPATH=. .venv/bin/python skills/chatbi-semantic-query/scripts/chatbi_semantic_query.py "按区域看1月到4月销售额排行" --chart-html /tmp/chatbi-region-sales.html
PYTHONPATH=. .venv/bin/python skills/chatbi-semantic-query/scripts/chatbi_semantic_query.py "按月看客户留存率趋势" --chart-html /tmp/chatbi-retention-trend.html
```

From the repo root, prefer the full script path shown above. If you `cd` into the skill directory, run `../../.venv/bin/python ./scripts/chatbi_semantic_query.py ...`.

## Supported Semantics

- Metrics come from `metric_definition`.
- Aliases come from `alias_mapping`, for example mapping business wording like `收入` to a governed metric such as `销售额`.
- Dimensions are loaded from `dimension_definition`. Common demo dimensions include `区域`, `月份`, `时间`, `部门`, `产品类别`, `产品名称`, `渠道`, and `客户类型`; when `时间` is used as a generic phrase, the current parser tends to map it to monthly grouping.
- Dimension synonyms are driven by `alias_mapping` first, with only a thin code fallback for generic wording such as `各区域`, `按月`, `趋势`, or `来源渠道`.
- Filters are inferred from distinct enum-like values in the source table, for example region, channel, product, or customer-type values that actually exist in the selected table.
- Time expressions include explicit year-month phrases like `YYYY年M月`, year-month ranges like `YYYY年M月到N月`, and month-only phrases like `1-4月` or `1月到4月`.
- Month ranges without a year use the latest year found in the selected fact table; if no year can be inferred from data, the parser falls back to `CHATBI_DEFAULT_YEAR`.
- Ranking expressions include `排行`, `排名`, `最高`, `最低`, `top N`, and `前 N`; ranking without an explicit dimension defaults to `区域` when the metric supports it.
- Structured output may include `data.plan_summary` and `data.plan_trace` for query-plan display or SSE thinking steps.
- Structured output may include top-level `chart_plan` for downstream renderers and top-level `kpis` for single-value summaries.
- `--chart-html` output uses standalone HTML + SVG. Monthly results use a line chart; other grouped results use a bar chart.

## Visualization Guidance

When returning structured results for a UI, include or recommend a chart plan alongside the business explanation. Pick the default chart from the user's intent and result shape, not from the skill name alone.

- Use a bar chart for categorical comparisons, rankings, highest/lowest questions, and region/channel/product/department breakdowns.
- Use a line chart for monthly or time trend questions, especially when the result has `月份`, `时间`, or `month`.
- Use a pie chart for composition, share, proportion, or contribution questions where categories sum to a meaningful whole.
- Use KPI cards for single-scope metric summaries, such as one region's sales, target achievement, gross margin, or retention. In the current protocol these are returned via top-level `kpis`, not `chart_plan.chart_type`.
- Highlight the best or worst category when the user asks for `最高`, `最低`, `最好`, `最差`, ranking, or anomaly detection.
- For UI rendering, prefer interactive ECharts options with tooltip, legend filtering, click highlight, and dataZoom for time series.
- For `--chart-html`, expect a lightweight static HTML + SVG preview rather than interactive ECharts.

Suggested chart plan shape for downstream renderers:

```json
{
  "chart_type": "bar|line|pie",
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

Illustrative structured payload shape for manual `--json` use:

```json
{
  "kind": "table",
  "text": "查询完成，共返回 N 条结果。",
  "data": {
    "question": "<时间范围><维度><指标>排行",
    "sql": "SELECT ...",
    "rows": [],
    "plan_summary": {
      "metric": "销售额",
      "metric_code": "sales_amount",
      "source_table": "sales_order",
      "dimensions": ["区域"],
      "filters": [],
      "time_filter": "`order_date` >= 'YYYY-MM-01' AND `order_date` < 'YYYY-MM-01'",
      "order_by_metric_desc": true,
      "limit": null
    },
    "plan_trace": [
      "收到问数请求：<时间范围><维度><指标>排行",
      "识别时间范围：`order_date` >= 'YYYY-MM-01' AND `order_date` < 'YYYY-MM-01'",
      "生成 SQL：SELECT ..."
    ]
  },
  "chart_plan": {
    "chart_type": "bar",
    "title": "<时间范围><维度><指标>排行",
    "dimension": "区域",
    "metrics": ["销售额"],
    "highlight": {"mode": "max", "field": "销售额"}
  },
  "kpis": []
}
```

## Database Defaults

The bundled script reads connection settings from `CHATBI_DB_*`.

- Agents should prefer the environment-backed settings and should not assume fixed credentials in prompts or downstream docs.
- The concrete fallback values live in `skills/_shared/db.py` via `default_db()` and may change with the local demo environment.

Override with environment variables:

- `CHATBI_DB_HOST`
- `CHATBI_DB_PORT`
- `CHATBI_DB_USER`
- `CHATBI_DB_PASSWORD`
- `CHATBI_DB_NAME`
- `CHATBI_DEFAULT_YEAR` for the parser's last-resort year fallback when the question omits a year and table data cannot provide one

## Safety

Use this skill for read-only semantic queries. The script should generate `SELECT` queries from governed metadata and whitelist-like table/field handling. Do not execute destructive SQL. Do not bypass the semantic query script unless the user explicitly asks for raw SQL investigation.

If the database is running in Docker and local MySQL access is blocked by the sandbox, request permission to run the script with elevated local network access.
