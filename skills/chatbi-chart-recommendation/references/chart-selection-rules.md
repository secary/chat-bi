# Chart Selection Rules

Use this matrix after identifying analysis intent and data shape.

## Primary Chart Matrix

| analysis_intent | data shape | recommended_chart | fallback |
| --- | --- | --- | --- |
| kpi | single_metric | kpi_card | table |
| kpi | single_metric with comparison | kpi_card_with_delta | bar |
| trend | metric_by_time | line | bar |
| trend | multi_metric_by_time | multi_line | grouped_bar |
| trend | category_by_time with <= 6 series | multi_line | stacked_bar |
| trend | category_by_time with > 6 series | stacked_bar | table |
| ranking | ranked_category | horizontal_bar | table |
| comparison | metric_by_category | grouped_bar | horizontal_bar |
| comparison | time + comparison period | line_with_delta | grouped_bar |
| composition | category + metric | stacked_bar or treemap | pie |
| composition | time + category + metric | stacked_bar | area |
| distribution | numeric metric rows | histogram | box_plot |
| relationship | two_metrics | scatter | table |
| matrix | two categories + metric | heatmap | pivot_table |
| detail | detail_rows | table | none |
| geospatial | geo + metric | map | bar |
| anomaly | time + metric | line_with_annotations | table |

## Banking-Specific Recommendations

- Branch ranking: `horizontal_bar`, sorted descending, limit 10 or user's requested N.
- Customer manager ranking: `horizontal_bar` or `table` if names and supporting fields are important.
- Risk classification composition: `stacked_bar` or `treemap`; avoid pie if categories include long labels.
- NPL ratio trend: `line` with percent y-axis; include threshold line if provided.
- Deposit or loan balance trend: `line`, amount axis in 万元 or 亿元.
- Business line comparison: `grouped_bar` for one period; `multi_line` for time trend.
- Customer detail list: `table`, even when numeric metrics exist.

## Anti-Patterns

- Do not recommend pie charts for ranking, trends, negative values, or many categories.
- Do not use line charts for unordered categories.
- Do not use dual-axis charts unless the user explicitly compares metrics with different units and the renderer supports it.
- Do not hide long-tail categories without noting the transform.
- Do not aggregate again if upstream SQL already aggregated to the requested grain.

## Transform Hints

- Ranking: sort descending by metric and apply limit.
- Top N with long tail: optionally add `other_bucket` only for composition views.
- Time trend: sort by time ascending and fill missing time buckets only if the frontend supports it.
- Percent share: compute `value / sum(value)` within the selected grouping scope.
- Heatmap: pivot two categorical dimensions and aggregate metric.
