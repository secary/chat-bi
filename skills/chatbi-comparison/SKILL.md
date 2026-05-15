---
name: chatbi-comparison
description: Use when the user asks for month-over-month (环比) comparison of business metrics such as sales, gross margin, order count, or customer count. Triggers on phrases like "环比", "上月对比", "月度对比", "和上个月比", "比上月", "月环比". Returns a comparison table with absolute change and percentage change, plus a grouped bar chart plan.
trigger_conditions:
  - 用户问环比、月度对比、比上月/上月、月环比
when_not_to_use:
  - 普通排行或趋势问数（用 chatbi-semantic-query）
  - 对话主题是上传文件分析
required_context:
  - 首参为用户原问句；演示数据默认 2026 年
validator_requires:
  - no_upload_path_in_thread
---

# ChatBI Comparison

Use this skill to calculate month-over-month (环比) comparison for governed metrics across any supported dimension.

## Workflow

1. Use `scripts/chatbi_comparison.py` when the user asks to compare metrics between two months.
2. Pass the user's original natural-language question as the first argument. **`N月份` is treated like `N月`** when inferring months (e.g. `1月份和2月份` ≡ `1月和2月`).
3. The script infers the current month and previous month from the question, defaulting to the latest two months in the data if not specified.
4. Results include: current period value, previous period value, absolute change, and percentage change.

## Common Commands

```bash
python3 scripts/chatbi_comparison.py "1月份和2月份销售额环比"
python3 scripts/chatbi_comparison.py "4月和3月销售额环比"
python3 scripts/chatbi_comparison.py "各区域销售额环比"
python3 scripts/chatbi_comparison.py "上月和本月毛利率对比"
python3 scripts/chatbi_comparison.py "按渠道看销售额环比变化"
python3 scripts/chatbi_comparison.py "订单数月度环比"
```

## Supported Metrics

- 销售额 / 收入 / 成交额
- 毛利 / 毛利额
- 毛利率
- 订单数
- 客户数
- 目标完成率

## Supported Dimensions

- 区域 / 大区（default when no dimension specified）
- 渠道
- 产品类别
- 客户类型
- 部门
- 总体（no grouping）

## Visualization Guidance

- Use a grouped bar chart when comparing across a dimension (e.g., region).
- Use KPI cards when comparing overall totals with no dimension.
- Highlight positive change in green, negative change in red.

## Database Defaults

Same as `chatbi-semantic-query`: overridable via `CHATBI_DB_*` environment variables.

## Safety

Read-only SELECT queries only.
