# 当前迭代任务

> 状态标记：📋 待开始 | 🚧 进行中 | ✅ 已完成 | ❌ 有问题

## 迭代目标
完成 ChatBI MVP：初始化演示数据库和语义层，验证 3 个 Skill 脚本，接入 Agent + FastAPI SSE，并实现 React 前端对话、思考步骤、图表和 KPI 卡片渲染。

## 任务清单

### 任务 1：数据库初始化
- 状态：📋 待开始
- 验收标准：
  - [ ] `docker compose up` 可以启动 MySQL 8.0
  - [ ] `chatbi_demo` 包含 `sales_order`、`customer_profile` 和语义层元数据表
  - [ ] 演示数据覆盖 2026 年 1-4 月和华东、华南、华北、西南区域
- 涉及文件：`docker-compose.yml`、`init_db/init.sql`、`.env.example`
- 复杂度：中

### 任务 2：Skill 脚本验证
- 状态：📋 待开始
- 验收标准：
  - [ ] `chatbi_semantic_query.py` 支持 `--show-sql` 和 `--json`
  - [ ] `add_alias_mapping.py` 可以插入已验证别名并输出 `--print-init-sql`
  - [ ] `generate_decision_advice.py` 可以输出 Markdown 和 `--json`
  - [ ] `SKILL.md` 明确声明脚本入口、输出形态、可视化/展示建议和安全边界
- 涉及文件：`skills/**/SKILL.md`、`skills/**/scripts/*.py`
- 复杂度：中

### 任务 3：Agent Skill 调度
- 状态：📋 待开始
- 验收标准：
  - [ ] AgentRunner 读取 `skills/*/SKILL.md`
  - [ ] System Prompt 包含 Skill 触发条件、工作流、可视化建议和安全边界
  - [ ] Agent 可以根据用户意图选择 3 个现有 Skill
  - [ ] Agent 可以根据 Skill 建议、用户意图和数据形态生成 chart plan
  - [ ] 脚本异常被转换为 `error` 类型消息
- 涉及文件：`backend/agent/runner.py`、`backend/agent/prompt_builder.py`
- 复杂度：高

### 任务 4：FastAPI SSE 接口
- 状态：📋 待开始
- 验收标准：
  - [ ] `POST /chat` 接收用户消息和会话历史
  - [ ] SSE 逐步输出 `thinking`、`text`、`chart`、`kpi_cards`、`error`、`done`
  - [ ] 首个 thinking 步骤在 1 秒内返回
- 涉及文件：`backend/main.py`、`backend/config.py`、`backend/agent/runner.py`
- 复杂度：高

### 任务 5：前端对话界面
- 状态：📋 待开始
- 验收标准：
  - [ ] `useChat` 管理消息列表、SSE 连接、输入和 loading 状态
  - [ ] `MessageBubble` 按 `type` 分发渲染
  - [ ] `ThinkingBubble` 支持逐步追加和折叠
- 涉及文件：`frontend/src/components/*.tsx`、`frontend/src/hooks/useChat.ts`、`frontend/src/types/message.ts`
- 复杂度：高

### 任务 6：图表与 KPI 渲染
- 状态：📋 待开始
- 验收标准：
  - [ ] 支持柱状图、折线图、饼图
  - [ ] 图表支持 tooltip、图例筛选和数据点高亮
  - [ ] 趋势图支持 dataZoom 或等效的时间范围筛选
  - [ ] renderer 可以根据 chart plan 生成 ECharts option
  - [ ] KPI 卡片支持 `success`、`warning`、`danger`、`neutral` 语义色
- 涉及文件：`frontend/src/components/ChartRenderer.tsx`、`frontend/src/components/KPICards.tsx`
- 复杂度：中

### 任务 7：端到端联调验收
- 状态：📋 待开始
- 验收标准：
  - [ ] 跑通自然语言问数场景
  - [ ] 跑通别名补充后再次问数场景
  - [ ] 跑通经营决策建议场景
  - [ ] Python 和 TypeScript 质量检查通过
- 涉及文件：`backend/`、`frontend/`、`skills/`、`docs/`
- 复杂度：高

## Gap 追踪（每次执行后更新）
| 轮次 | 完成内容 | 发现问题 | 下一步 |
|------|---------|---------|-------|
| - | Harness Engineering 初始化 | 尚未开始实现 MVP 功能 | 初始化完成，等待开发 |
| 1 | 补充 Skill 可视化指导与交互式图表要求 | 尚未实现 Agent chart plan、renderer 和前端图表交互 | 从任务 1 开始，后续在任务 3 和任务 6 落地可视化链路 |
