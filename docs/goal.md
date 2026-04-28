# 项目目标

## 核心目标
跑通 ChatBI MVP 的完整链路：用户用中文自然语言提问，Agent 选择合适 Skill，调用确定性脚本查询或维护 MySQL 语义层，并通过前端以思考步骤、文字结论、图表和 KPI 卡片呈现结果。

## 成功标准（MVP 验收）
- [ ] 用户可以用中文提问经营指标，例如销售额、目标完成率、毛利率和客户留存率
- [ ] Agent 可以自动选择 `chatbi-semantic-query`、`chatbi-alias-manager` 或 `chatbi-decision-advisor`
- [ ] `chatbi-semantic-query` 可以生成受语义层约束的只读 SQL 并返回表格或 JSON 结果
- [ ] `chatbi-alias-manager` 可以向 `alias_mapping` 插入已验证的指标或维度别名
- [ ] `chatbi-decision-advisor` 可以先计算指标事实，再输出 Markdown 或 JSON 决策建议
- [ ] 前端可以通过 SSE 展示 `thinking`、`text`、`chart`、`kpi_cards` 和 `error` 消息
- [ ] 图表支持柱状图、折线图、饼图和基础交互
- [ ] SSE 首字节，即第一个 thinking 步骤，在 1 秒内到达
- [ ] Docker Compose 可以一键启动 MySQL 和 Backend，前端可通过 `npm run dev` 本地开发
- [ ] Python 通过 black + ruff，TypeScript 通过 ESLint + Prettier

## 非目标（这次不做）
- 不做登录、权限、多租户隔离
- 不做前端 Docker 化，前端本期使用本地 dev server
- 不做文件上传作为数据源
- 不做运行时动态模型切换，模型通过 `.env` 配置
- 不做独立后端工具注册层，原子能力优先封装在 Skill 脚本中
- 暂不考虑企业级 LDAP、SSO、行列级权限、审计日志和数据脱敏
