# Analysis Intent Taxonomy

Use these labels to identify what the user is trying to understand. Prefer the user's analysis goal over the literal SQL shape.

## Intent Labels

| intent | goal | common signals | banking examples |
| --- | --- | --- | --- |
| kpi | Read one headline number | 多少, 总量, 当前, 截至, 余额, 规模 | 上月对公存款余额是多少 |
| trend | See change over time | 趋势, 走势, 变化, 每月, 近N天, 年初至今 | 近12个月贷款余额走势 |
| ranking | Compare entities ordered by value | 排名, 前N, 后N, 最高, 最低, 哪些最多 | 上月支行存款余额前10 |
| comparison | Compare groups or periods | 对比, 比较, 同比, 环比, 较年初, 对公和个人 | 对公贷款余额同比变化 |
| composition | Understand part-to-whole | 占比, 构成, 分布, 结构, 各类占多少 | 各贷款品种余额占比 |
| distribution | Understand spread across many values | 分布, 区间, 离散, 集中, 异常 | 客户AUM分布 |
| relationship | Explore correlation between two metrics | 关系, 相关, 是否影响, X和Y | 支行存款余额和客户数关系 |
| detail | Inspect raw or drill-down rows | 明细, 列表, 清单, 哪些客户 | 逾期贷款客户明细 |
| geospatial | Compare by location | 地图, 地区, 省份, 城市 | 各省个人贷款余额分布 |
| anomaly | Find unusual changes or outliers | 异常, 波动, 突增, 突降, 告警 | 哪些支行不良率异常升高 |

## Intent Priority

When multiple signals appear, use this priority:

1. detail
2. anomaly
3. trend with comparison
4. ranking
5. composition
6. relationship
7. distribution
8. kpi

Examples:

- `近一年各月对公贷款余额同比` -> trend with comparison.
- `各支行存款余额排名前10` -> ranking.
- `贷款余额按五级分类占比` -> composition.
- `哪些客户逾期明细` -> detail.

## Ambiguity Rules

- "分布" can mean composition by category or statistical distribution by numeric buckets. Use field shape to decide.
- "变化" usually means trend if a time field exists; otherwise comparison against a base period.
- "排名" implies sort and often limit. If no entity dimension exists, ask which object to rank.
- "占比" requires a meaningful denominator. If denominator is missing, ask or compute from the same grouped result when valid.
