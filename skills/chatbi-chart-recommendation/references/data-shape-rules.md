# Data Shape Rules

Inspect available fields before recommending a chart.

## Field Roles

Classify fields as:

- `time`: date, month, quarter, year, stat_date, accounting_date.
- `metric`: numeric amount, count, balance, ratio, percentage, score.
- `category`: branch, product, channel, business line, customer segment, risk level, industry.
- `identifier`: customer_id, account_id, contract_id, card_id, transaction_id.
- `geo`: province, city, region, latitude, longitude.

Use upstream Query Intent roles when available. Otherwise infer from names and values.

## Data Shape Labels

| shape | condition | likely charts |
| --- | --- | --- |
| single_metric | one row, one metric | kpi_card |
| metric_by_time | one time field, one metric | line, area, bar |
| multi_metric_by_time | one time field, multiple metrics | multi_line, grouped_bar |
| metric_by_category | one category, one metric | horizontal_bar, bar |
| ranked_category | category + metric + sort/limit | horizontal_bar |
| category_by_time | time + category + metric | multi_line, stacked_bar, grouped_bar |
| composition | category + metric + part-to-whole semantics | stacked_bar, treemap, pie |
| two_metrics | two metrics, optional category | scatter |
| matrix | two categories + metric | heatmap, pivot_table |
| detail_rows | many identifiers or many columns | table |

## Cardinality Guidance

- 1 metric, 0 dimensions, 1 row: KPI card.
- 1 category with 2 to 20 rows: bar or horizontal bar.
- 1 category with more than 20 rows: sorted bar with limit or table.
- Time series with 3 or more time points: line chart.
- Time series with only 1 or 2 time points: bar or KPI with delta.
- Two categories with up to 15 x 15 cells: heatmap.
- More than 50 rows and many identifiers: table with pagination.
- Pie chart only when categories are 2 to 5, values are non-negative, and the question asks for share/composition.

## Value Semantics

- Ratios and percentages need percent formatting.
- Amounts need unit formatting: CNY, 万元, 亿元, or local default.
- Negative values should not use pie or treemap.
- Mixed units should not share one y-axis unless normalized.
- Large branch/product names should use horizontal bars or tables.
