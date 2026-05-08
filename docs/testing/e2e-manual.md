# E2E 手动验证用例

面向功能验证，不替代自动化测试。每次发版前或改动 Agent/Skill 逻辑后执行。

## 一键自动运行

```bash
# 启动后端
docker compose -f docker-compose.dev.yml up -d

# 运行全部用例（需 LLM API Key 已配置）
python scripts/e2e_smoke.py

# 只跑指定用例
python scripts/e2e_smoke.py --cases S1,M1,C1

# 开启鉴权时传 token
python scripts/e2e_smoke.py --token "Bearer xxx"

# 指定后端地址（默认 8001）
python scripts/e2e_smoke.py --url http://localhost:8000

# 也可以用环境变量，便于临时接入 CI 或同事机器
CHATBI_E2E_URL=http://localhost:8001 python scripts/e2e_smoke.py --cases S1,S4,E1
```

脚本会逐条打印 ✓ / ✗，最终输出通过率。用例覆盖范围见下方各节。

---

## 准备（浏览器手动验证）

1. 启动完整环境：`docker compose -f docker-compose.dev.yml up -d`
2. 浏览器打开 `http://localhost:5174`
3. 打开 DevTools → Network，过滤 `/chat`，观察 SSE 流中 `thinking` 步骤的 skill 名称

---

## 一、单 Skill

| # | 输入 | 预期触发 Skill | 预期输出 |
|---|------|--------------|---------|
| S1 | `1-4月各区域销售额排行` | `chatbi-semantic-query` | 柱状图 + 区域/销售额数据 |
| S2 | `2026年销售额按月趋势` | `chatbi-semantic-query` | 折线图 + 逐月数据 |
| S3 | `华东4月毛利率` | `chatbi-semantic-query` | KPI 卡片 |
| S4 | `当前数据库有哪些表可以查` | `chatbi-database-overview` | 表清单 + 字段说明文本 |
| S5 | `销售额和上月相比怎么样` | `chatbi-comparison` | 环比表格 + 分组柱状图 |
| S6 | `销售额口径是什么` | `chatbi-metric-explainer` | 指标说明文本 |
| S7 | `把"营收"设为"销售额"的别名` | `chatbi-alias-manager` | 确认别名写入的文字回复 |

---

## 二、多步 Skill（Legacy Runner）

触发条件：问题同时命中 `_QUERY_RE`（排行/趋势/销售额等）和 `_DECISION_RE`（建议/意见）。

| # | 输入 | 预期步骤 | 验证点 |
|---|------|---------|-------|
| M1 | `1-4月各区域销售额排行，并给出经营建议` | semantic-query → decision-advisor | 思考步骤出现两段；先有数据图表，再有建议文本 |
| M2 | `各渠道毛利率经营建议` | semantic-query → decision-advisor | 建议内容聚焦"毛利率"维度，不是泛泛综合建议 |
| M3 | `华东销售额建议` | semantic-query → decision-advisor | 建议内容聚焦华东区域 |

---

## 三、图表渲染（ReAct 多步）

验证 `react_runner._merge_finish_result` 修复：当 skill 已生成 `chart_plan` 时，不被 LLM finish 文本覆盖，回复中不出现原始 ECharts JSON。

| # | 输入 | 预期 | 不应出现 |
|---|------|------|---------|
| C1 | `请把下面结果用最合适的图表可视化出来：{"question":"2026年1-4月销售额趋势","rows":[{"月份":"2026-01","销售额":355000},{"月份":"2026-02","销售额":378000},{"月份":"2026-03","销售额":412000},{"月份":"2026-04","销售额":462000}]}` | 直接渲染折线图 + skill 自带分析文本 | 回复文本中出现 `"series":` / `"xAxis":` 等原始 JSON 片段 |
| C2 | `2026年销售额按月趋势`（不附数据，让 ReAct 自行查） | ReAct 多步：chart-recommendation → semantic-query → 渲染图表，文本为趋势分析 | 同上，无原始 JSON |

---

## 四、边界场景

| # | 输入 | 预期 |
|---|------|------|
| E1 | `你好` 或 `谢谢` | 直接文字回复；SSE 流中**不出现** `agent.skill.started` 事件 |
| E2 | `2024年销售额`（年份不存在） | 提示无对应年份数据，不编造数字 |
| E3 | 上传 `data/chatbi_sales.csv` 后发送 `分析这份数据并画图` | 触发 `chatbi-file-ingestion`；SSE 流中**不出现** `chatbi-semantic-query` |

---

## 五、外部数据库接入（chatbi_bank_external）

### 前置：导入外部银行库

```bash
# 在能连接目标 MySQL 的环境中执行（本机 3306 或容器内）
mysql -h 127.0.0.1 -P 3306 -u root -p < database/external_bank_bootstrap.sql
mysql -h 127.0.0.1 -P 3306 -u root -p < database/external_bank_demo.sql
```

数据库用户：`demo_user` / `demo_pass`，库名：`chatbi_bank_external`

### 前置：在管理页添加数据源连接

1. 进入「数据源」管理页 → 新增连接
2. 填写：Host=`host.docker.internal`（或 `127.0.0.1`）、Port=`3306`、Database=`chatbi_bank_external`、User=`demo_user`、Password=`demo_pass`
3. 点击「测试连接」确认成功
4. 勾选「设为默认」并保存

### 功能验证

| # | 输入 | 预期触发 Skill | 验证点 |
|---|------|--------------|-------|
| X1 | `当前数据库有哪些表可以查` | `chatbi-database-overview` | 返回 `bank_branch`、`loan_contract`、`wealth_position` 等银行表；兼容视图 `sales_order`/`customer_profile` 也在列表中 |
| X2 | `1-4月各支行业务余额排行` | `chatbi-semantic-query` | 按 `department`（网点/支行）维度出柱状图；数值单位为万元级别 |
| X3 | `各业务类型收入贡献趋势` | `chatbi-semantic-query` | 折线图，维度为 `product_category`（存款业务/贷款业务/财富管理） |
| X4 | `AUM是什么意思` | `chatbi-metric-explainer` | 返回语义层中 `business_amount`/`AUM` 的字段说明 |
| X5 | `贷款余额经营建议` | semantic-query → decision-advisor | 先查 `loan_contract` 相关数据，建议聚焦贷款风险或余额维度 |
| X6 | `各渠道AUM和上月对比` | `chatbi-comparison` | 按 `channel`（客户经理/财富顾问等）维度的环比分组柱状图 |

### 切回演示库验证隔离

1. 管理页将默认数据源切回 `chatbi_demo`
2. 发送 `1-4月各区域销售额排行` → 应返回演示库数据（华东/华南/华北/西南区域），**不出现**银行相关字段

---

## 通用检查点

- SSE `thinking` 步骤中的 skill 名称与预期一致
- 图表可交互（tooltip、图例筛选）
- KPI 卡片状态色正确（高完成率 → success，低 → danger）
- 切换会话后再回来，消息不丢失
- 发送消息后切页再返回，助手回复正常出现
