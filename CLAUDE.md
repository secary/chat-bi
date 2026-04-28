# CLAUDE.md — ChatBI Agent 工作手册

## 项目简介
ChatBI 是面向银行业务场景的对话式数据分析 Demo，让用户用中文自然语言完成问数、语义别名维护和经营决策建议生成。

## 技术栈
- Backend: FastAPI + Python 3.11 + LiteLLM
- Frontend: React 18 + TypeScript + Vite + Tailwind CSS + ECharts 5
- Database: MySQL 8.0 via Docker Compose, local port 3307
- Skills: `skills/<skill-name>/SKILL.md` + 确定性 Python 脚本 + 本地 `mysql` CLI
- Streaming: SSE
- Quality: Python black + ruff; TypeScript ESLint + Prettier

## 快速导航
| 做什么 | 看哪里 |
|--------|--------|
| 系统架构 | docs/architecture/overview.md |
| 模块边界 | docs/architecture/boundaries.md |
| 编码规范 | docs/conventions/README.md |
| 当前迭代 | docs/plans/current-sprint.md |
| 功能设计 | docs/design/ |
| 项目目标 | docs/goal.md |

## 硬性规则
1. 依赖方向：types/ → lib/utils/ → services/ → app/（不得反向引用）
2. 单文件不超过 300 行
3. 每个新功能必须有对应测试文件
4. 禁止使用 console.log，使用项目统一的 logger
5. API 调用统一通过封装的 apiClient，禁止裸 fetch()
6. Skill 新增删除只改 `skills/<skill-name>/SKILL.md` 与可选 `scripts/` 文件
7. 问数和决策建议脚本只执行 `SELECT`
8. 数据库连接通过 `CHATBI_DB_*` 环境变量覆盖默认值

## 工作流程

### 每次开始工作时（必须执行）
1. 读取 `AGENTS.md`，理解项目全局规则
2. 读取 `docs/plans/current-sprint.md`，了解当前状态
3. 读取当前任务对应的 `docs/design/` 文件（如果有）
4. 列出当前 Gap：当前状态 vs 验收标准，差距在哪里
5. 确认验收标准已定义，否则禁止开始编码

### 执行过程中
- 每完成一个文件，主动运行相关测试
- 发现 Linter 错误，立即修复，不要跳过
- 遇到模糊需求，查阅 `docs/` 文档，不要自行假设
- Skill 相关改动必须同步 `SKILL.md`、脚本入口和安全边界
- 每次修改不超过 5 个文件（拆分成多轮）
- 不确定需求时直接查阅文档，禁止自行假设

### 每次完成任务后（必须执行）
1. 运行所有测试，报告通过/失败情况
2. 更新 `docs/plans/current-sprint.md` 对应任务的状态
3. 在 Gap 追踪表中追加本轮记录
4. 明确告诉用户：下一个最高优先级的 Gap 是什么

## 禁止行为
- 禁止跳过测试直接标记任务完成
- 禁止在没有验收标准的情况下开始编码
- 禁止修改 `AGENTS.md` 和 `docs/goal.md`（除非用户明确要求）
- 禁止一次性修改超过 5 个文件（拆分成多轮）
- 禁止让 LLM 绕过 Skill 脚本直接编造指标事实
