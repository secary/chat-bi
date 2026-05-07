# Frontend Component Mapping

Use this mapping to produce renderer-ready component names and props. If the project has a concrete chart library, override these names with local component names.

## Generic Component Map

| chart_type | component_name | library_type | core props |
| --- | --- | --- | --- |
| kpi_card | MetricCard | metric | valueField, label, unit, numberFormat |
| kpi_card_with_delta | MetricCard | metric | valueField, deltaField, deltaType, trendField |
| line | LineChart | line | xField, yField, seriesField, smooth=false |
| multi_line | LineChart | line | xField, yField, seriesField |
| line_with_delta | LineChart | line | xField, yField, comparisonField, deltaField |
| bar | BarChart | bar | xField, yField, layout=horizontal |
| horizontal_bar | BarChart | bar | xField, yField, layout=vertical |
| grouped_bar | BarChart | bar | xField, yField, seriesField, group=true |
| stacked_bar | BarChart | bar | xField, yField, seriesField, stack=true |
| area | AreaChart | area | xField, yField, seriesField, stack optional |
| pie | PieChart | pie | angleField, colorField |
| treemap | TreemapChart | treemap | valueField, categoryField |
| scatter | ScatterChart | scatter | xField, yField, colorField, sizeField optional |
| heatmap | HeatmapChart | heatmap | xField, yField, colorField |
| table | DataTable | table | columns, pagination, sortable |
| map | GeoMap | map | geoField, valueField |

## Encoding To Props

- `encodings.x.field` -> `xField`
- `encodings.y.field` -> `yField`
- `encodings.series.field` -> `seriesField`
- `encodings.color.field` -> `colorField`
- `encodings.size.field` -> `sizeField`
- `encodings.tooltip[].field` -> `tooltipFields`
- `options.limit` -> `limit`
- `options.sort` -> `sortOrder`
- `options.unit` -> `unit`
- `options.number_format` -> `numberFormat`
- `options.percent_format` -> `percentFormat`
- `options.interactions` -> `interactions`

## Interaction Defaults

| chart_type | interactions |
| --- | --- |
| kpi_card | tooltip, drilldown |
| line | tooltip, legend_filter, brush_zoom |
| bar | tooltip, drilldown, data_label_toggle |
| horizontal_bar | tooltip, drilldown, data_label_toggle |
| grouped_bar | tooltip, legend_filter, drilldown |
| stacked_bar | tooltip, legend_filter, drilldown |
| pie | tooltip, legend_filter |
| treemap | tooltip, drilldown |
| scatter | tooltip, brush_select |
| heatmap | tooltip, drilldown |
| table | sort, filter, pagination, export |

## Empty And Sparse Data

- Empty result: return `status: "table_only"` with warning `empty_result`, no chart component.
- One row and one metric: use `MetricCard`.
- One category row and one metric: use `MetricCard` or `DataTable`; avoid bar charts that show a single bar unless the user asked for comparison.
- Many columns with identifiers: use `DataTable`.

## Prop Hygiene

- Do not emit props for fields that are not present in result metadata or Query Intent.
- Use stable component names and generic props unless the user provides the frontend framework contract.
- Keep display labels separate from field IDs when possible: `xField` should use field ID, `xLabel` should use display name.
