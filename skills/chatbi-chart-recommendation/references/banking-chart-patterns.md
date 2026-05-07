# Banking Chart Patterns

Use these patterns after identifying analysis intent and data shape. They encode banking BI preferences and common question types.

## Metric Patterns

| banking question pattern | intent | primary chart | notes |
| --- | --- | --- | --- |
| 存款余额走势, 存款规模变化, 存款趋势 | trend | line | Use amount axis with compact CNY formatting. |
| 贷款余额走势, 信贷余额变化 | trend | line | Use line; add comparison series for 同比/环比 if present. |
| 不良率走势, 不良贷款率变化 | trend | line | Percent y-axis; include threshold line if available. |
| 手机银行活跃用户趋势 | trend | line | Count formatting; daily/monthly grain from data. |
| 支行排名, 网点排名, 客户经理排名 | ranking | horizontal_bar | Sort descending; default Top 10 if user asks ranking without N. |
| 前10客户, 大客户排行 | ranking | horizontal_bar or table | Use table if identifiers and multiple metrics matter. |
| 业务线对比, 对公个人对比 | comparison | grouped_bar | Use multi_line if there is a time axis. |
| 同比, 环比, 较年初 | comparison | kpi_card_with_delta or line_with_delta | KPI for one metric/one period; line for multi-period. |
| 五级分类构成, 风险分类占比 | composition | stacked_bar or treemap | Avoid pie if labels are long or categories exceed 5. |
| 产品结构, 渠道结构, 客群结构 | composition | stacked_bar or treemap | Use stacked bar if comparing across time/org. |
| 客户分层分布, AUM分布 | distribution | bar or histogram | Category tiers -> bar; numeric buckets -> histogram. |
| 明细, 清单, 列表 | detail | table | Add sort/filter/export interactions. |
| 地区分布, 省份分布, 城市分布 | geospatial | map or bar | Use map only if frontend supports geo and region codes exist. |

## Banking Formatting

- Amount metrics: format as compact CNY, usually 万元 or 亿元.
- Ratio metrics: format as percentages with 2 decimal places unless local rule differs.
- Count metrics: integer format with comma separators.
- Balance metrics: include snapshot period in subtitle when known.
- Period-sum metrics: include period range in subtitle when known.

## Multi-Chart Recommendations

Recommend secondary charts when one question naturally needs context:

- Trend plus latest ranking: primary `line`, secondary `horizontal_bar`.
- NPL analysis: primary `line` for ratio trend, secondary `stacked_bar` for risk classification composition.
- Branch performance: primary `horizontal_bar`, secondary `table` with supporting metrics.
- Customer segmentation: primary `stacked_bar` or `treemap`, secondary `table`.

## Rejection Rules

- Reject pie for branch rankings, customer rankings, or long category names.
- Reject line when x-axis is branch, product, customer manager, or unordered category.
- Reject map when no region code/name exists or frontend has no map component.
- Reject scatter unless at least two numeric metrics exist.
- Reject stacked chart when there is no series/category field.

## Confidence Guidance

- 0.90 to 1.00: explicit intent plus matching data shape.
- 0.75 to 0.89: strong chart match but one minor assumption, such as default Top 10.
- 0.55 to 0.74: chartable but ambiguous wording or imperfect data shape.
- Below 0.55: ask clarification or return table-only.
