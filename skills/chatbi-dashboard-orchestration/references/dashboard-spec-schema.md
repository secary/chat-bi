# Dashboard Spec Schema

Emit a single JSON object. Do not wrap it in Markdown when machine-readable output is requested.

## Schema

```json
{
  "status": "ready",
  "original_query": "",
  "dashboard_intent": "",
  "dashboard_title": "",
  "confidence": 0.0,
  "layout": {
    "grid_columns": 12,
    "row_height": 80,
    "density": "comfortable"
  },
  "global_filters": [],
  "sections": [],
  "widgets": [],
  "interactions": [],
  "responsive": {
    "desktop": {"columns": 12},
    "tablet": {"columns": 12},
    "mobile": {"columns": 1}
  },
  "data_dependencies": [],
  "decision_factors": [],
  "warnings": [],
  "missing_inputs": []
}
```

## Status Values

- `ready`: enough chart specs or data summaries exist to build a dashboard.
- `need_clarification`: dashboard goal or critical inputs are missing.
- `single_chart_only`: only one chart exists and no dashboard-level structure is justified.
- `unsupported`: inputs cannot be arranged into a meaningful dashboard.

## Widget Shape

```json
{
  "id": "widget_1",
  "type": "chart",
  "chart_type": "line",
  "title": "",
  "section_id": "section_1",
  "priority": 1,
  "position": {"x": 0, "y": 0, "w": 8, "h": 5},
  "chart_spec_ref": null,
  "chart_spec": {},
  "data_ref": null,
  "visible": true
}
```

## Example

Input: dashboard from charts for `对公贷款风险分析`

```json
{
  "status": "ready",
  "original_query": "生成对公贷款风险分析看板",
  "dashboard_intent": "risk_analysis",
  "dashboard_title": "对公贷款风险分析看板",
  "confidence": 0.9,
  "layout": {
    "grid_columns": 12,
    "row_height": 80,
    "density": "comfortable"
  },
  "global_filters": [
    {"field": "time_range", "label": "统计期", "type": "date_range", "required": true},
    {"field": "branch_id", "label": "机构", "type": "tree_select", "required": false},
    {"field": "industry_code", "label": "行业", "type": "select", "required": false}
  ],
  "sections": [
    {"id": "summary", "title": "核心指标", "order": 1},
    {"id": "trend", "title": "风险趋势", "order": 2},
    {"id": "breakdown", "title": "结构与排名", "order": 3},
    {"id": "detail", "title": "明细清单", "order": 4}
  ],
  "widgets": [
    {
      "id": "npl_ratio_card",
      "type": "kpi",
      "chart_type": "kpi_card_with_delta",
      "title": "不良贷款率",
      "section_id": "summary",
      "priority": 1,
      "position": {"x": 0, "y": 0, "w": 3, "h": 2},
      "chart_spec_ref": "chart_npl_ratio_card",
      "chart_spec": {},
      "data_ref": "query_npl_ratio",
      "visible": true
    },
    {
      "id": "npl_trend",
      "type": "chart",
      "chart_type": "line",
      "title": "不良贷款率趋势",
      "section_id": "trend",
      "priority": 1,
      "position": {"x": 0, "y": 2, "w": 8, "h": 5},
      "chart_spec_ref": "chart_npl_ratio_trend",
      "chart_spec": {},
      "data_ref": "query_npl_ratio_trend",
      "visible": true
    },
    {
      "id": "risk_class_composition",
      "type": "chart",
      "chart_type": "stacked_bar",
      "title": "五级分类构成",
      "section_id": "breakdown",
      "priority": 2,
      "position": {"x": 0, "y": 7, "w": 6, "h": 5},
      "chart_spec_ref": "chart_risk_class",
      "chart_spec": {},
      "data_ref": "query_risk_class",
      "visible": true
    },
    {
      "id": "high_risk_detail",
      "type": "table",
      "chart_type": "table",
      "title": "高风险贷款明细",
      "section_id": "detail",
      "priority": 4,
      "position": {"x": 0, "y": 12, "w": 12, "h": 6},
      "chart_spec_ref": "chart_high_risk_table",
      "chart_spec": {},
      "data_ref": "query_high_risk_detail",
      "visible": true
    }
  ],
  "interactions": [
    {
      "type": "brush_time",
      "source_widget_id": "npl_trend",
      "target_widget_ids": ["risk_class_composition", "high_risk_detail"],
      "time_field": "stat_date"
    },
    {
      "type": "table_detail",
      "source_widget_id": "risk_class_composition",
      "target_widget_id": "high_risk_detail",
      "join_fields": ["risk_level"]
    }
  ],
  "responsive": {
    "desktop": {"columns": 12},
    "tablet": {"columns": 12},
    "mobile": {"columns": 1}
  },
  "data_dependencies": ["query_npl_ratio", "query_npl_ratio_trend", "query_risk_class", "query_high_risk_detail"],
  "decision_factors": [
    "risk metrics indicate risk_analysis dashboard",
    "KPI plus trend plus composition plus detail creates a complete risk story"
  ],
  "warnings": [],
  "missing_inputs": []
}
```
