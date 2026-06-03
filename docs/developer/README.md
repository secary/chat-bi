# ChatBI 开发者手册

本文面向需要本地开发、测试、二次扩展和排查实现问题的研发人员。

## 1. 项目概览

ChatBI 是银行场景的对话式数据分析 Demo：

- 前端：React 19、TypeScript、Vite、Tailwind CSS、ECharts 6。
- 后端：FastAPI、Python 3.11+、LiteLLM。
- 数据库：MySQL 8.0。
- Agent 能力：`skills/<skill-name>/SKILL.md` + 可选确定性 Python 脚本。
- 质量入口：ruff、black、ESLint、`scripts/run_tests.py`。

核心边界见 [架构文档](../architecture/README.md)，实现细节见 [技术实现指南](../guide/tech-guide.md)。

## 2. 本地开发启动

首次或依赖变动：

```bash
bash scripts/bootstrap_dev.sh --sync
```

日常进入：

```bash
bash scripts/bootstrap_dev.sh
```

启动开发服务：

```bash
bash scripts/start_dev.sh
```

默认端口：

| 服务 | 端口 |
|---|---|
| 前端 Vite | `5173` |
| 后端 FastAPI | `8000` |
| 本机开发 MySQL | `3306` |
| Docker 生产式 MySQL | `3307` |

本地开发配置通常放在 `.env.dev`。后端通用加载只读 `.env`，开发脚本由 `scripts/start_dev.sh` 显式读取 `.env.dev`。

## 3. 生产式本地验证

使用默认 Docker Compose：

```bash
cp .env.example .env
bash scripts/launch.sh --no-open
```

常用命令：

```bash
docker compose ps
docker compose logs -f
docker compose down
```

部署与 GitHub Actions CD 详见 [CI/CD 文档](../ci-cd/README.md)。

## 4. 代码结构

| 路径 | 说明 |
|---|---|
| `frontend/` | React 前端、页面、组件、hooks、API client |
| `backend/` | FastAPI 路由、Agent 编排、配置、存储、渲染 |
| `skills/` | Skill 文档和确定性脚本 |
| `database/` | MySQL 初始化脚本、业务数据和语义层 |
| `scripts/` | 启动、测试、格式化、审计辅助脚本 |
| `tests/` | Python 测试 |
| `docs/` | 用户、管理员、开发者和内部参考文档 |

## 5. Agent 执行主线

后端统一入口是 `backend/agent/runner.py` 的 `stream_chat`。

默认前端发送 `multi_agents="auto"`：

```text
auto -> decide_execution_mode
  -> ask: 返回澄清问题
  -> single: 单 Agent ReAct 或 Legacy
  -> multi: 多 Agent 专线编排
```

单 Agent 默认走 ReAct：LLM 输出 JSON 步进，调用 Skill，Observation 回灌，最后 `finish` 收口。

多 Agent 由 Manager 规划任务，再交给 registry 中的专线执行，最后汇总。默认专线包括上传分析、演示库问数、跨期对比、图表看板、语义配置和经营建议。

详细规则见 [技术实现指南](../guide/tech-guide.md)。

## 6. Skill 开发规则

Skill 目录结构：

```text
skills/<skill-name>/
  SKILL.md
  scripts/
```

规则：

- `SKILL.md` 描述触发条件、不要使用场景、必备上下文、工作流和安全边界。
- 脚本输出必须归一为 SkillResult：`kind`、`text`、`data`、`charts`、`kpis`。
- 问数和决策建议脚本只执行 `SELECT`。
- 脚本可以依赖 `skills/_shared/`，不得反向依赖 FastAPI 路由或前端。
- 新增或删除 Skill 时，只改 `skills/<skill-name>/SKILL.md` 与可选 `scripts/`，并补充对应测试。

## 7. 前后端边界

后端依赖方向：

```text
config.py -> prompt_builder.py -> planner/executor/formatter -> runner.py -> main.py
```

前端 API 调用统一走 `apiClient`，禁止裸 `fetch()`。组件不应了解 SQL 或 Skill 脚本细节。

渲染模块只负责把结构化结果转为前端消息，不查询或修改数据库。

## 8. 测试与格式化

代码改动后先跑格式化：

```bash
.venv/bin/python scripts/format_code.py
```

按改动范围选择测试套件：

```bash
PYTHONPATH=. .venv/bin/python scripts/run_tests.py quick -- -q
PYTHONPATH=. .venv/bin/python scripts/run_tests.py agent -- -q
PYTHONPATH=. .venv/bin/python scripts/run_tests.py admin -- -q
```

前端：

```bash
cd frontend && npm run lint && npm run test && npm run build
```

新增 `tests/test_*.py` 时，必须注册到 `scripts/run_tests.py` 的 `MODULE_SUITES`。完整测试说明见 [测试文档](../testing/README.md)。

## 9. 编码规范

重点规则：

- 单文件不超过 300 行。
- 禁止 `console.log`。
- 用户可见错误要友好，技术细节写入日志。
- SQL 标识符和字面量必须安全转义。
- 指标和维度优先来自语义层表。
- 新功能必须补测试。

完整规则见 [编码规范](../conventions/README.md)。

## 10. 排查入口

| 问题 | 优先看 |
|---|---|
| Agent 路由异常 | `backend/agent/execution_decider.py`、`multi_agent_intent.py`、trace 日志 |
| Skill 没被选中 | Skill frontmatter、`admin_skill_registry`、prompt 构造 |
| SSE 前端显示异常 | `backend/agent/formatter.py`、`frontend/src/hooks/useChat.ts` |
| 上传分析异常 | `backend/agent/upload_context.py`、`chatbi-file-ingestion`、`chatbi-auto-analysis` |
| 登录和权限异常 | 鉴权配置、用户表、前端路由守卫 |
| CI 失败 | [测试文档](../testing/README.md)、[CI/CD 文档](../ci-cd/README.md) |
