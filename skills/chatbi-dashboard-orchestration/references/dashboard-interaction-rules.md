# Dashboard Interaction Rules

Emit interaction contracts that the frontend can implement without guessing.

## Global Filters

Common banking global filters:

- `time_range`
- `business_line`
- `branch`
- `region`
- `product`
- `customer_segment`
- `channel`
- `currency`

Only include filters that are present in Query Intent, chart specs, or field metadata. Mark filters as `optional` if they may not apply to all widgets.

## Cross-Widget Interactions

| interaction | use when | output fields |
| --- | --- | --- |
| cross_filter | charts share a dimension such as branch, product, risk_level | source_widget_id, target_widget_ids, field |
| drilldown | hierarchy exists such as region > branch > customer_manager | hierarchy, source_field, target_view |
| brush_time | multiple time-series charts share time axis | source_widget_id, target_widget_ids, time_field |
| legend_filter | stacked/multi-series charts | field, applies_to |
| table_detail | chart click opens detail table | source_widget_id, target_widget_id, join_fields |
| export | table or whole dashboard | scope, formats |

## Banking Interaction Defaults

- Branch ranking click filters other charts by branch.
- Product composition click filters ranking and detail tables by product.
- Risk classification click filters risk ranking and detail table.
- Time brush on a trend chart updates all widgets using the same time field.
- Detail tables should support sort, filter, pagination, and export.

## Safety Rules

- Do not define cross-filter interactions between widgets that do not share a field.
- Do not define drilldown hierarchies unless the hierarchy is present or conventional in the field names.
- If a widget uses aggregated data and a detail table uses record-level data, include join fields and note any grain mismatch.
