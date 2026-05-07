# Query Intent Schema

Emit a single JSON object. Do not wrap it in Markdown when the user asks for machine-readable output.

## Schema

```json
{
  "status": "ready",
  "original_query": "",
  "language": "zh-CN",
  "business_line": "unknown",
  "domain": "",
  "intent_type": "analysis",
  "metrics": [
    {
      "metric_id": "",
      "name": "",
      "aggregation": "",
      "formula": null,
      "unit": null
    }
  ],
  "dimensions": [
    {
      "dimension_id": "",
      "name": "",
      "role": "group_by"
    }
  ],
  "filters": [
    {
      "dimension_id": "",
      "operator": "=",
      "value": "",
      "normalized_value": ""
    }
  ],
  "time": {
    "time_range": {
      "start": "",
      "end": "",
      "type": "natural_period"
    },
    "grain": null,
    "point_in_time": false,
    "calendar_type": "natural"
  },
  "comparison": {
    "type": null,
    "base_range": null,
    "calculation": null
  },
  "sort": [
    {
      "field": "",
      "direction": "desc"
    }
  ],
  "limit": null,
  "missing_slots": [],
  "clarification_questions": [],
  "ambiguities": [],
  "assumptions": [],
  "sql_readiness": {
    "ready_for_text_to_sql": true,
    "schema_hints": [],
    "notes": []
  }
}
```

## Status Values

- `ready`: the intent is complete enough for Text-to-SQL.
- `need_clarification`: one or more required slots are missing or ambiguous.
- `unsupported`: the request is outside banking BI semantic parsing.

## Intent Types

- `analysis`: ordinary metric query.
- `ranking`: top N or rank query.
- `comparison`:同比, 环比, 较期初, multi-period, or multi-entity comparison.
- `trend`: time-series query.
- `detail`: drill-down or record-level query.
- `definition`: business meaning or metric explanation.

## Ready Example

User: `上月各支行存款余额排名前10`

```json
{
  "status": "ready",
  "original_query": "上月各支行存款余额排名前10",
  "language": "zh-CN",
  "business_line": "unknown",
  "domain": "deposit",
  "intent_type": "ranking",
  "metrics": [
    {
      "metric_id": "deposit_balance",
      "name": "存款余额",
      "aggregation": "sum",
      "formula": null,
      "unit": "CNY"
    }
  ],
  "dimensions": [
    {
      "dimension_id": "branch",
      "name": "支行",
      "role": "group_by"
    }
  ],
  "filters": [],
  "time": {
    "time_range": {
      "start": "PREVIOUS_MONTH_START",
      "end": "PREVIOUS_MONTH_END",
      "type": "natural_period"
    },
    "grain": "month",
    "point_in_time": true,
    "calendar_type": "natural"
  },
  "comparison": {
    "type": null,
    "base_range": null,
    "calculation": null
  },
  "sort": [
    {
      "field": "deposit_balance",
      "direction": "desc"
    }
  ],
  "limit": 10,
  "missing_slots": [],
  "clarification_questions": [],
  "ambiguities": [],
  "assumptions": [
    "用户未指定对公或个人，按全行汇总口径理解。",
    "存款余额按月末时点余额理解。",
    "币种默认人民币。"
  ],
  "sql_readiness": {
    "ready_for_text_to_sql": true,
    "schema_hints": [],
    "notes": []
  }
}
```

## Clarification Example

User: `客户排名`

```json
{
  "status": "need_clarification",
  "original_query": "客户排名",
  "language": "zh-CN",
  "business_line": "unknown",
  "domain": "customer",
  "intent_type": "ranking",
  "metrics": [],
  "dimensions": [
    {
      "dimension_id": "branch",
      "name": "机构",
      "role": "candidate_group_by"
    }
  ],
  "filters": [],
  "time": {
    "time_range": null,
    "grain": null,
    "point_in_time": false,
    "calendar_type": "natural"
  },
  "comparison": {
    "type": null,
    "base_range": null,
    "calculation": null
  },
  "sort": [],
  "limit": null,
  "missing_slots": ["metric"],
  "clarification_questions": [
    "请问按哪个指标做客户排名？例如客户数、新增客户数、AUM余额或存款余额。"
  ],
  "ambiguities": [
    {
      "slot": "metric",
      "candidates": ["customer_count", "new_customer_count", "aum_balance", "deposit_balance"]
    }
  ],
  "assumptions": [],
  "sql_readiness": {
    "ready_for_text_to_sql": false,
    "schema_hints": [],
    "notes": ["缺少排名指标，暂不能生成可靠SQL。"]
  }
}
```
