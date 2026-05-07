# Chart Spec Schema

Emit one JSON object. Do not wrap in Markdown when machine-readable output is requested.

## Schema

```json
{
  "status": "ready",
  "original_query": "",
  "analysis_intent": "",
  "data_shape": "",
  "confidence": 0.0,
  "recommended_chart": {
    "type": "",
    "frontend_component": {
      "name": "",
      "library_type": "",
      "props": {}
    },
    "title": "",
    "subtitle": "",
    "encodings": {
      "x": null,
      "y": null,
      "series": null,
      "color": null,
      "size": null,
      "tooltip": []
    },
    "transforms": [],
    "options": {
      "orientation": null,
      "stack": false,
      "sort": null,
      "limit": null,
      "unit": null,
      "number_format": null,
      "percent_format": false,
      "show_legend": true,
      "show_data_labels": false,
      "interactions": ["tooltip"]
    }
  },
  "secondary_charts": [],
  "fallback_charts": [],
  "decision_factors": [],
  "rejected_charts": [],
  "reasoning_summary": "",
  "warnings": [],
  "missing_inputs": []
}
```

## Status Values

- `ready`: enough fields exist to render the recommended chart.
- `need_clarification`: missing user intent or missing chart-critical field.
- `table_only`: data is better represented as a table.
- `unsupported`: requested chart or data shape cannot be handled.

## Example: Branch Ranking

Input question: `上月各支行对公存款余额排名前10`

```json
{
  "status": "ready",
  "original_query": "上月各支行对公存款余额排名前10",
  "analysis_intent": "ranking",
  "data_shape": "ranked_category",
  "confidence": 0.94,
  "recommended_chart": {
    "type": "horizontal_bar",
    "frontend_component": {
      "name": "BarChart",
      "library_type": "bar",
      "props": {
        "layout": "vertical",
        "xField": "corporate_deposit_balance",
        "yField": "branch_name",
        "seriesField": null,
        "sortBy": "corporate_deposit_balance",
        "sortOrder": "desc",
        "limit": 10
      }
    },
    "title": "上月各支行对公存款余额排名前10",
    "subtitle": "按对公存款余额降序",
    "encodings": {
      "x": {"field": "corporate_deposit_balance", "type": "metric"},
      "y": {"field": "branch_name", "type": "category"},
      "series": null,
      "color": null,
      "size": null,
      "tooltip": [
        {"field": "branch_name", "type": "category"},
        {"field": "corporate_deposit_balance", "type": "metric"}
      ]
    },
    "transforms": [
      {"type": "sort", "field": "corporate_deposit_balance", "order": "desc"},
      {"type": "limit", "value": 10}
    ],
    "options": {
      "orientation": "horizontal",
      "stack": false,
      "sort": "desc",
      "limit": 10,
      "unit": "CNY",
      "number_format": "compact",
      "percent_format": false,
      "show_legend": false,
      "show_data_labels": true,
      "interactions": ["tooltip", "drilldown"]
    }
  },
  "secondary_charts": [],
  "fallback_charts": ["table"],
  "decision_factors": [
    "analysis_intent=ranking",
    "one category dimension and one amount metric",
    "branch names are usually long, so horizontal bars improve readability"
  ],
  "rejected_charts": [
    {
      "type": "pie",
      "reason": "排名比较不适合饼图。"
    },
    {
      "type": "line",
      "reason": "没有时间序列字段。"
    }
  ],
  "reasoning_summary": "用户要看排名，数据为机构维度加单一金额指标，支行名称较长，横向条形图最易比较。",
  "warnings": [],
  "missing_inputs": []
}
```

## Example: Need Clarification

Input question: `看看分布`

```json
{
  "status": "need_clarification",
  "original_query": "看看分布",
  "analysis_intent": "distribution",
  "data_shape": "unknown",
  "confidence": 0.2,
  "recommended_chart": {
    "type": null,
    "frontend_component": {
      "name": null,
      "library_type": null,
      "props": {}
    },
    "title": "",
    "subtitle": "",
    "encodings": {
      "x": null,
      "y": null,
      "series": null,
      "color": null,
      "size": null,
      "tooltip": []
    },
    "transforms": [],
    "options": {
      "orientation": null,
      "stack": false,
      "sort": null,
      "limit": null,
      "unit": null,
      "number_format": null,
      "percent_format": false,
      "show_legend": true,
      "show_data_labels": false,
      "interactions": ["tooltip"]
    }
  },
  "secondary_charts": [],
  "fallback_charts": [],
  "decision_factors": [
    "user mentioned distribution",
    "no data preview or field metadata was provided"
  ],
  "rejected_charts": [],
  "reasoning_summary": "用户只表达了分布意图，但没有可判断的指标、维度或数据字段。",
  "warnings": [],
  "missing_inputs": ["metric_or_field", "data_preview"]
}
```
