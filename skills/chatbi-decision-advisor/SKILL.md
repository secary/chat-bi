---
name: chatbi-decision-advisor
description: Use when Codex or another agent needs to generate rule-based decision recommendations from the local ChatBI demo database by computing sales, target achievement, gross margin, region, channel, product, and customer retention metrics first, then deriving structured business advice, actions, priorities, and evidence. Use for 决策意见, 经营建议, 管理建议, 下一步动作, and recommendation generation from existing ChatBI data.
trigger_conditions:
  - 用户要经营建议、决策意见、管理建议或下一步动作
  - 问题含区域/渠道/产品等业务范围可供脚本取数
when_not_to_use:
  - 用户只要单一指标查询结果（用 chatbi-semantic-query）
  - 对话主题是上传文件分析
required_context:
  - 演示库问数场景；首参保留用户原述
---

# ChatBI Decision Advisor

Use this skill to produce decision advice from computed ChatBI metrics.

## Workflow

1. Run `scripts/generate_decision_advice.py` to calculate facts from MySQL and produce rule-based advice.
2. Use Markdown output for human-facing decision notes.
3. Use `--json` when another agent, report generator, or dashboard needs structured facts and recommendations.
4. Treat the advice as deterministic rule output grounded in metrics. If an LLM is used later, use it only to rewrite or summarize the generated facts and advice.
5. Use `chatbi-semantic-query` separately when the user asks for one specific metric query rather than a full decision recommendation.

## Commands

```bash
python3 scripts/generate_decision_advice.py
python3 scripts/generate_decision_advice.py --json
python3 scripts/generate_decision_advice.py "华东2026年4月决策建议"
python3 scripts/generate_decision_advice.py --question "线上渠道软件服务决策建议" --json
```

Run commands from this skill directory, or pass the full path to the bundled script.

## What It Computes

- Overall sales, target achievement, gross margin, order count, and customer count.
- Monthly sales trend and monthly margin/target completion.
- Region sales, target achievement, and gross margin ranking.
- Channel sales and gross margin ranking.
- Product category sales and gross margin ranking.
- Monthly customer retention, churn, active customers, and new customers.

## Natural-Language Scope

The optional question can limit the advice scope by:

- Time: `2026年4月`, `2026年1月到4月`, `2026年`
- Region: values such as `华东`, `华南`, `华北`, `西南`
- Department: values such as `商业增长部`, `数据产品部`, `咨询服务部`
- Product category/name: values such as `软件服务`, `数据产品`, `咨询服务`, `智能分析平台`
- Channel: values such as `线上`, `渠道`, `直销`
- Customer type: values such as `企业客户`, `中小客户`

When the scope includes sales-only dimensions such as channel, product, or department, omit customer-retention advice because `customer_profile` does not contain those fields.

## Advice Rules

- High target achievement triggers growth target and replication advice.
- Low target achievement triggers gap-closing advice.
- Positive monthly sales growth triggers growth consolidation advice.
- Region ranking triggers regional replication and weak-area follow-up advice.
- Channel and product margin ranking triggers portfolio optimization advice.
- Customer retention triggers retention and churn management advice.
- Low gross margin triggers profitability repair advice.

## Visualization Guidance

Use this skill's structured JSON facts to produce an executive-style answer: decision text first, then KPI cards and focused supporting charts. Do not ask the LLM to invent chart data; charts must come from computed facts.

- Use KPI cards for overview facts: sales, target achievement, gross margin, order count, customer count, and latest retention.
- Use a line chart for monthly sales, monthly target achievement, monthly gross margin, or retention trends.
- Use a bar chart for region, channel, or product category rankings.
- Use semantic colors in KPI cards: `success` for strong target achievement, `warning` for moderate risks, `danger` for low achievement or low margin, and `neutral` for context metrics.
- Keep advice text and charts linked: every chart should support one recommendation or evidence point in the advice.
- Prefer tooltip, legend filtering, click highlight, and dataZoom for monthly trend charts.

## Database Defaults

The bundled script defaults to:

- Host: `127.0.0.1`
- Port: `3307`
- Database: `chatbi_demo`
- User: `demo_user`
- Password: `demo_pass`

Override with environment variables:

- `CHATBI_DB_HOST`
- `CHATBI_DB_PORT`
- `CHATBI_DB_USER`
- `CHATBI_DB_PASSWORD`
- `CHATBI_DB_NAME`

## Safety

This skill runs read-only `SELECT` queries. Do not make database changes with this skill.
