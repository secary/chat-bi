# Dashboard Intent Rules

Identify the dashboard goal before arranging widgets.

## Dashboard Intent Types

| intent | goal | common inputs | banking examples |
| --- | --- | --- | --- |
| overview | Give an executive overview | KPI cards + trend + breakdowns | 全行经营概览, 对公业务总览 |
| monitoring | Track current status and alerts | KPI cards + anomaly/risk lists | 不良贷款监控, 存款波动监控 |
| performance | Compare entities and rank results | rankings + KPI + detail | 支行经营排名, 客户经理业绩看板 |
| risk_analysis | Explain risk level and change | risk KPI + trend + composition + detail | 不良贷款分析, 逾期贷款分析 |
| customer_analysis | Understand customers and segments | customer KPIs + segmentation + trend | 个人客户经营分析 |
| product_analysis | Analyze product structure and sales | product KPIs + composition + ranking | 理财产品销售看板 |
| channel_analysis | Analyze digital/channel behavior | channel KPIs + trend + channel breakdown | 手机银行活跃用户分析 |
| detail_audit | Inspect records and exceptions | tables + filters + export | 逾期客户清单, 大额交易明细 |

## Intent Selection

- If the user asks for "看板", "大屏", "总览", or "概览", choose `overview`.
- If the user asks for "监控", "预警", "异常", or "波动", choose `monitoring`.
- If the main intent is ranking branches, products, or managers, choose `performance`.
- If metrics include 不良, 逾期, 风险分类, or 五级分类, choose `risk_analysis`.
- If metrics include 客户数, 新增客户, 活跃客户, AUM, or 客群, choose `customer_analysis`.
- If data is mostly rows and identifiers, choose `detail_audit`.

## Story Order

Use this order unless the user specifies otherwise:

1. Current status: headline KPIs.
2. Change over time: trend and comparisons.
3. Breakdown: business line, branch, product, risk level, channel, or customer segment.
4. Accountability: rankings by branch, customer manager, product, or region.
5. Detail: exception list or drilldown table.
