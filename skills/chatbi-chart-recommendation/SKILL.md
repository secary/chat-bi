---
name: chatbi-chart-recommendation
description: BI chart recommendation for ChatBI and analytics workflows. Use when Codex needs to choose chart types and emit frontend-ready chart recommendation JSON from a user's analysis intent, Query Intent JSON, SQL result metadata, or tabular data, especially after natural language to SQL to data pipelines.
trigger_conditions:
  - 已有 SQL 结果、表格 rows 或 Observation 中的查询数据
  - 用户问适合什么图表、如何可视化已有结果
when_not_to_use:
  - 尚未取数、无 rows 或 preview_rows
  - 用户只要原始数值、未要求可视化
required_context:
  - 上一步取数或上传解析的 Observation
validator_requires:
  - prior_observation
---

# Chart Recommendation

Use this skill after semantic parsing, SQL execution, or data preview to recommend a chart that matches the user's analysis intent and the returned data shape.

## Workflow

1. Preserve the original user question and upstream Query Intent JSON if provided.
2. Identify analysis intent with `references/analysis-intent-taxonomy.md`.
3. Inspect the result data shape with `references/data-shape-rules.md`:
   - metric count
   - dimension count
   - time dimension
   - row count
   - categorical cardinality
   - positive/negative values
   - percentage or ratio fields
4. Apply banking-specific chart patterns with `references/banking-chart-patterns.md`.
5. Select chart type with `references/chart-selection-rules.md`.
6. Map the chart type to frontend component and props with `references/frontend-component-mapping.md`.
7. Produce frontend-ready JSON matching `references/chart-spec-schema.md`.
8. Include `confidence`, `decision_factors`, `rejected_charts`, `reasoning_summary`, and fallback options.
9. Do not invent unavailable fields. If required fields are missing, return `status: "need_clarification"` or `status: "table_only"`.

## Recommendation Priorities

Prefer charts that answer the analysis question directly:

- Trend intent: line chart before bar chart.
- Ranking intent: sorted horizontal bar before pie.
- Comparison intent: grouped bar or line depending on time axis.
- Composition intent: stacked bar or treemap; pie only for very small part-to-whole views.
- Distribution intent: histogram, box plot, or density-like chart if supported.
- Relationship intent: scatter plot when two numeric metrics exist.
- KPI intent: single-value card, optionally with delta and sparkline.
- Detail intent: table.

For banking BI, choose conservative business charts over decorative charts. Optimize for readability, auditability, and repeated decision-making.

## Banking BI Defaults

- Use table when data is too sparse, too wide, or mostly identifiers.
- Use horizontal bars for branch/customer manager/product rankings because names are often long.
- Use line charts for month, quarter, day, or year trends.
- Use stacked bars for business-line, product, channel, or risk-class composition across organizations or time.
- Avoid pie charts when categories exceed 5, labels are long, values contain negatives, or percentages do not sum to a meaningful whole.
- Use KPI cards for single aggregated metrics such as total deposit balance, NPL ratio, or mobile active users.

## Output Contract

Always emit valid JSON following `references/chart-spec-schema.md`.

The output should be usable by a frontend chart renderer. Include:

- `recommended_chart`
- `frontend_component`
- field encodings for `x`, `y`, `series`, `color`, `tooltip`
- component props for axis, legend, data labels, formatting, and interactions
- transform hints such as sort, limit, aggregate, percent, or pivot
- rendering options such as title, subtitle, axis labels, unit, number format, and interaction hints
- confidence and rejected chart reasons
- fallback charts

If the upstream system has a fixed chart library, map the recommended chart to that library's supported chart type names. If no library is specified, use generic names like `line`, `bar`, `horizontal_bar`, `grouped_bar`, `stacked_bar`, `kpi_card`, `table`, `scatter`, `heatmap`, `treemap`, `pie`.

## Reference Files

- `references/analysis-intent-taxonomy.md`: analysis intent labels and trigger patterns.
- `references/data-shape-rules.md`: how to infer chartability from result fields and rows.
- `references/chart-selection-rules.md`: chart recommendation matrix and anti-patterns.
- `references/banking-chart-patterns.md`: banking-specific question patterns and chart preferences.
- `references/frontend-component-mapping.md`: generic chart types mapped to frontend components and props.
- `references/chart-spec-schema.md`: frontend-ready recommendation JSON schema and examples.
