---
name: chatbi-metric-explainer
description: Use when Codex or another agent needs to explain a governed metric's business meaning, formula, source table, default dimensions, related fields, or口径 in ChatBI. Trigger for requests such as 指标解释, 口径说明, 销售额怎么算, 毛利率是什么意思, 目标完成率定义, and 指标来源.
trigger_conditions:
  - 用户问指标含义、口径、公式、来源，不要数值结果
when_not_to_use:
  - 用户要实际查询指标值（用 chatbi-semantic-query）
  - 用户要维护别名映射（用 chatbi-alias-manager）
required_context:
  - 问题中含指标名或业务别名
---

# ChatBI Metric Explainer

Use this skill when the user wants an explanation of a metric rather than a metric value query.

## Workflow

1. Run `scripts/explain_metric.py` with the user's original Chinese question.
2. Let the script map aliases such as `收入` to the governed metric name in `metric_definition`.
3. Return the explanation text directly. The output is already formatted for chat display.
4. If the user later wants the actual metric result, switch to `chatbi-semantic-query`.

## Commands

```bash
python3 scripts/explain_metric.py "销售额口径是什么"
python3 scripts/explain_metric.py "解释一下毛利率" --json
python3 scripts/explain_metric.py "目标完成率怎么算"
python3 scripts/explain_metric.py "收入这个指标是什么意思" --json
```

Run commands from this skill directory, or pass the full path to the bundled script.

## Coverage

- Governed metrics come from `metric_definition`.
- Alias matching comes from `alias_mapping`.
- Related field meaning comes from `field_dictionary`.
- The response focuses on: standard metric name, metric code, source table, formula, business caliber, default dimensions, and related fields.

## Presentation Guidance

Return concise executive-friendly text. Do not generate business charts for metric explanation results unless the user explicitly asks for a visual breakdown of the formula.

## Safety

This skill only reads semantic metadata tables. It must not modify MySQL data or write semantic aliases.
