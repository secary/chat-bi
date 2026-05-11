# 当前迭代任务

> 状态标记：📋 待开始 | 🚧 进行中 | ✅ 已完成 | ❌ 有问题

## 迭代目标
完成 ChatBI MVP：初始化演示数据库和语义层，验证 3 个 Skill 脚本，接入 Agent + FastAPI SSE，并实现 React 前端对话、思考步骤、图表和 KPI 卡片渲染。

## 任务清单

### 任务 1：数据库初始化
- 状态：✅ 已完成
- 验收标准：
  - [x] `docker compose up` 可以启动 MySQL 8.0
  - [x] `chatbi_demo` 包含 `sales_order`、`customer_profile` 和语义层元数据表
  - [x] 演示数据覆盖 2026 年 1-4 月和华东、华南、华北、西南区域
- 涉及文件：`docker-compose.yml`、`database/init.sql`、`.env.example`
- 复杂度：中

### 任务 2：Skill 脚本验证
- 状态：📋 待开始（用户要求暂时跳过）
- 验收标准同上
- 复杂度：中

### 任务 3：Agent Skill 调度
- 状态：✅ 已完成
- 验收标准：
  - [x] AgentRunner 读取 `skills/*/SKILL.md`
  - [x] System Prompt 包含 Skill 触发条件、工作流、可视化建议和安全边界
  - [x] Agent 可以根据用户意图选择 3 个现有 Skill
  - [x] Agent 可以根据 Skill 建议、用户意图和数据形态生成 chart plan
  - [x] 脚本异常被转换为 `error` 类型消息
- 涉及文件：`backend/agent/runner.py`、`backend/agent/prompt_builder.py`
- 复杂度：高

### 任务 4：FastAPI SSE 接口
- 状态：✅ 已完成
- 验收标准：
  - [x] `POST /chat` 接收用户消息和会话历史
  - [x] SSE 逐步输出 `thinking`、`text`、`chart`、`kpi_cards`、`error`、`done`
  - [x] 首个 thinking 步骤在 1 秒内返回
- 涉及文件：`backend/main.py`、`backend/config.py`、`backend/agent/runner.py`
- 复杂度：高

### 任务 5：前端对话界面
- 状态：✅ 已完成
- 验收标准：
  - [x] `useChat` 管理消息列表、SSE 连接、输入和 loading 状态
  - [x] `MessageBubble` 按 `type` 分发渲染
  - [x] `ThinkingBubble` 支持逐步追加和折叠
- 涉及文件：`frontend/src/components/*.tsx`、`frontend/src/hooks/useChat.ts`、`frontend/src/types/message.ts`
- 复杂度：高

### 任务 6：图表与 KPI 渲染
- 状态：✅ 已完成
- 验收标准：
  - [x] 支持柱状图、折线图、饼图
  - [x] 图表支持 tooltip、图例筛选和数据点高亮
  - [x] 趋势图支持 dataZoom 或等效的时间范围筛选
  - [x] renderer 可以根据 chart plan 生成 ECharts option
  - [x] KPI 卡片支持 `success`、`warning`、`danger`、`neutral` 语义色
- 涉及文件：`frontend/src/components/ChartRenderer.tsx`、`frontend/src/components/KPICards.tsx`
- 复杂度：中

### 任务 7：端到端联调验收
- 状态：🔄 待开始（需先配置 LLM API Key）
- 验收标准：
  - [ ] 跑通自然语言问数场景
  - [ ] 跑通别名补充后再次问数场景
  - [ ] 跑通经营决策建议场景
  - [ ] Python 和 TypeScript 质量检查通过
- 涉及文件：`backend/`、`frontend/`、`skills/`、`docs/`
- 复杂度：高

### 任务 8：会话记忆 + 管理导航（MVP）
- 状态：✅ 已完成
- 验收标准：
  - [x] `chatbi_demo` 增加 `chat_session` / `chat_message` / `skill_registry` / `app_db_connection` / `llm_settings`；`database/migrations/001_app_tables.sql` 供旧库增量执行
  - [x] `GET/POST/PATCH/DELETE /sessions` 与 `GET /sessions/{id}/messages`；`POST /chat` 支持 `session_id`、`db_connection_id`，助手回合落库
  - [x] Skill 子进程可注入默认或指定的数据源连接；LiteLLM 使用 `llm_settings` 合并覆盖 env
  - [x] `/admin/skills`、`/admin/db-connections`、`/admin/llm-settings` 管理接口；`scan_skills_enabled` 尊重禁用 Skill
  - [x] 前端左侧导航：对话 / 技能 / 数据源 / LLM；对话页会话列表、切换、新对话；管理页 CRUD
  - [x] `pytest` 19 项通过；前端 `eslint`、`npm run build` 通过
- 涉及文件：`backend/routes/*`、`backend/session_repo.py`、`backend/db_mysql.py`、`frontend/src/pages/*`、`database/init.sql`
- 复杂度：高

### 任务 9：数据仪表盘
- 状态：✅ 已完成
- 验收标准：
  - [x] `GET /dashboard/overview` 基于生效业务库（与 Skill 相同的连接解析）只读聚合 `sales_order`、`customer_profile` 及语义层表行数
  - [x] 前端左侧导航「仪表盘」，路由 `/dashboard`：KPI 卡片、区域饼图、按月柱状图、客户活跃度柱状图、语义层资产列表；Vite 代理 `/dashboard`
  - [x] `tests/test_dashboard_overview.py`、`frontend` Vitest `dashboardCharts.test.ts`
- 涉及文件：`backend/business_db.py`、`backend/dashboard_overview.py`、`backend/routes/dashboard_route.py`、`frontend/src/pages/DashboardPage.tsx`、`frontend/src/lib/dashboardCharts.ts`、`frontend/vitest.config.ts`
- 复杂度：中

### 任务 11：Multi-Agent、多模态与 PDF 报告
- 状态：✅ 已完成
- 验收标准：
  - [x] `skills/_agents/registry.yaml` 定义风控 / 营销 / 分析与 Skill 白名单；路由 LLM 输出专线列表（上限见 registry）；顺序执行专线并按 Observation 汇总输出；`POST /chat` 支持 `multi_agents`
  - [x] 前端「多专线协作」开关 + `localStorage`；`CHATBI_VISION_DISABLED` 可关闭图像抽取；`/upload` 支持 PNG/JPG/WebP；会话发起前对用户消息中的上传图像路径做 LiteLLM Vision 表格抽取并注入上下文
  - [x] `GET /sessions/{id}/report.pdf` 导出服务端 PDF（WeasyPrint）；前端「导出 PDF 报告」；镜像安装 Pango/Cairo 与 Noto CJK；`tests/test_multi_agent_*`、`test_vision_extract.py`、`test_report_pdf.py`
  - [x] PDF 报告：`litellm.completion` 精炼摘要（`CHATBI_PDF_SUMMARY_DISABLED` 时降级为要点摘录）；ECharts 落库 option 经 matplotlib 转 PNG 嵌入 HTML；ReportLab 降级路径含 PNG；`matplotlib`/`pillow` 依赖
  - [x] 对话页：多专线「iOS 风格」拨动开关（`Switch.tsx`）；会话侧栏可收起/展开（`chatbi_sidebar_open`）
- 涉及文件：`backend/agent/multi_agent_*.py`、`backend/vision/`、`backend/report/pdf_report.py`、`backend/report/pdf_summary.py`、`backend/report/pdf_chart_png.py`、`backend/routes/sessions_route.py`、`frontend/src/pages/ChatPage.tsx`、`frontend/src/components/Switch.tsx`、`frontend/src/hooks/useChat.ts`、`backend/Dockerfile`、`requirements.txt`
- 复杂度：高

### 任务 10：用户鉴权与长短期记忆（OpenClaw 风格 MVP）
- 状态：✅ 已完成
- 验收标准：
  - [x] `database/init.sql` 与 `database/migrations/002_users_and_memory.sql`：`app_user`、`chat_session.user_id`、`user_memory`；种子管理员 `admin` / `admin123`（部署后请改密）
  - [x] JWT：`POST /auth/login`、`GET /auth/me`；`/sessions`、`/chat`、`/dashboard`、`/upload` 需 `Authorization: Bearer`；`/admin/*` 需 `admin` 角色
  - [x] `GET /sessions` 返回 `{ sessions, suggested_prompts }`；`chat_session` 按 `user_id` 隔离
  - [x] 记忆：对话前注入长期偏好 + 近期会话摘要；回合结束后异步 LLM 摘要并合并长期记忆；环境变量 `CHATBI_MEMORY_DISABLED` 可关闭记忆链路
  - [x] 前端：登录页与 `RequireAuth`；管理员侧栏「用户管理」；对话区展示记忆快捷 chip；Vite 代理 `/auth`
  - [x] 测试：`tests/test_auth_password.py`、`tests/test_auth_tokens.py`、`tests/test_memory_service_off.py`；`npm run build` 通过
- 涉及文件：`backend/auth_deps.py`、`backend/auth_tokens.py`、`backend/user_repo.py`、`backend/memory_repo.py`、`backend/memory_service.py`、`backend/routes/auth_route.py`、`backend/routes/admin_users_route.py`、`frontend/src/api/client.ts`、`frontend/src/pages/ChatPage.tsx`
- 复杂度：高

### 任务 12：多 Agents 注册表管理（管理员）
- 状态：✅ 已完成
- 验收标准：
  - [x] `GET/PUT /admin/multi-agents` 读写 `skills/_agents/registry.yaml`（原子写入），校验专线 id、至少一条专线、技能 slug 须存在于 `scan_skills`
  - [x] 前端管理员侧栏「多Agents管理」、路由 `/multi-agents`：每轮上限、专线增删、`label`/`role_prompt`、技能多选（结合 `/admin/skills` 列表）
  - [x] `tests/test_admin_multi_agents.py`、`frontend/src/lib/multiAgentsRegistryUi.test.ts`；`npm run build` 通过
- 涉及文件：`backend/routes/admin_multi_agents_route.py`、`backend/agent/multi_agent_registry.py`、`backend/main.py`、`frontend/src/pages/MultiAgentsAdminPage.tsx`、`frontend/src/lib/multiAgentsRegistryUi.ts`、`frontend/src/App.tsx`、`frontend/src/components/AppLayout.tsx`
- 复杂度：中

## Gap 追踪（每次执行后更新）
| 轮次 | 完成内容 | 发现问题 | 下一步 |
|------|---------|---------|-------|
| - | Harness Engineering 初始化 | 尚未开始实现 MVP 功能 | 初始化完成，等待开发 |
| 1 | 补充 Skill 可视化指导与交互式图表要求 | 尚未实现 Agent chart plan、renderer 和前端图表交互 | 从任务 1 开始，后续在任务 3 和任务 6 落地可视化链路 |
| 2 | 调整数据库初始化结构并通过 `docker compose config` 校验 | 尚未实际执行 `docker compose up` 验证容器启动与初始化落库 | 启动 MySQL 容器并用 SQL 校验核心表与样例数据 |
| 3 | MySQL 容器启动并验证通过 + 完整后端(fastapi SSE, agent runner, prompt builder, renderers) + 完整前端(React chat UI, charts, KPI) | LLM API Key 尚未配置，无法进行端到端联调；MySQL CLI 在容器内而非宿主机 | 配置 LLM API Key 后验证完整链路 |
| 4 | 梳理 API Key 与数据库接入方式，并修复 `.env` 加载顺序、LiteLLM 参数透传、`.env.example` 示例 | 本机尚未创建 `.env`，实际 API Key 未配置 | 创建 `.env` 后启动后端并进行端到端联调 |
| 5 | 验证 `.env` 已包含 LLM、API_BASE 和数据库变量，确认 MySQL 容器与演示数据可用 | 后端虚拟环境尚未安装依赖；联网安装依赖授权被拒；Codex 沙箱直连 127.0.0.1:3307 受限 | 安装 `backend/requirements.txt` 后启动 FastAPI 做端到端联调 |
| 6 | 定位前端 `TypeError: Load failed`，补充 backend Docker 服务，修复容器内 MySQL SSL、MiniMax LiteLLM 模型配置和 fenced JSON 解析 | 端到端问数已在容器内跑通；仍需浏览器刷新后人工确认交互渲染 | 继续验证别名补充与经营决策建议场景 |
| 7 | 完整恢复 `stash@{0}` 中 tracked、deleted 和 untracked 文件，包括 Dockerfile、nginx 配置、Compose 三服务定义和脚本修正 | 当前改动已恢复到工作区但尚未提交；本地 `main` 仍与 `origin/main` 分叉 | 复核恢复内容后提交，或继续执行完整 `docker compose up --build` 验证 |
| 8 | 验证 MySQL、backend、frontend 容器均运行中；宿主机 MySQL CLI 可连 `chatbi_demo`；backend 容器内语义查询脚本可成功查询销售额排行 | 宿主机 Homebrew MySQL 9.6 不兼容脚本参数 `--ssl=0`，直接在宿主机跑语义脚本会失败 | 如需宿主机运行脚本，兼容 MySQL 9.x 的 SSL 参数；应用侧可继续用容器内脚本联调 |
| 9 | 增强自然语言短句触发：`1-4月销售额排行` 可默认使用 2026 年并按区域排行；Agent 对语义查询使用用户原句入参；前端示例改为短问法 | 前端 lint 因本地 `eslint` 未安装无法执行；运行中的 Docker 镜像尚未包含本次代码改动 | 重建 backend/frontend 容器后在浏览器验证短问法 |
| 10 | 修复语义查询脚本 MySQL SSL 参数兼容：优先尝试 `--ssl-mode=DISABLED`，再 fallback 到 MariaDB 客户端支持的 `--ssl=0` | 当前 backend 容器仍是旧镜像，容器内脚本仍会报 self-signed certificate，需重建后生效 | 执行 `docker compose up -d --build backend frontend` 后重新验证短问法 |
| 11 | 前端顶部标题和浏览器标题改为 `零眸智能 ChatBI` | 前端 lint 仍因本地 `eslint` 未安装无法执行；`frontend/index.html` 当前不在 Git 跟踪中 | 重建 frontend 容器并在浏览器确认标题展示 |
| 12 | 在 backend 容器内验证 3 个 Skill 脚本：语义查询短问法、决策建议 JSON、别名管理均执行成功；`营收` 已映射到 `销售额` 且可用于问数 | 别名验证新增了 `营收 -> 销售额` 到当前 MySQL 数据；如需重建后保留，应同步到初始化 SQL | 在前端分别验证问数、别名和决策建议完整交互 |
| 13 | 修复决策技能前端卡住：runner 将 decision-advisor JSON 渲染为 Markdown 文本，跳过普通表格图表/KPI 渲染，并重建 backend；`/chat` SSE 已返回完整文本和 `done` | 决策技能当前只输出文本建议，尚未为嵌套 facts 定制图表/KPI 渲染 | 在浏览器刷新后复测 `2026年1-4月经营决策建议` |
| 14 | 优化前端消息排版：新增轻量内容渲染，将 Markdown 标题、编号和列表转换为页面友好的层级文本；Docker 前端构建通过并重启容器 | 决策建议仍以文本为主，尚未拆成专门的建议卡片或趋势图 | 浏览器刷新后复测决策建议展示效果 |
| 15 | 完成第一阶段架构优化：新增统一 SkillResult 协议、`skills/_shared`、拆分 Agent planner/executor/formatter/runner，并补协议单测；backend 容器重建通过，3 个 Skill 脚本协议输出验证通过 | 两个历史大脚本仍超过 300 行，尚未拆分为 parser/rules/render 等子模块 | 第二阶段拆分 semantic-query 与 decision-advisor 大脚本，并补端到端回归 |
| 16 | 完成文档收口：`CLAUDE.md` 降级为 `AGENTS.md` 入口，合并架构 overview/boundaries 到 `docs/architecture/README.md`，归档历史 PRD，删除模板化 `frontend/README.md` | 文档结构已收敛，但 README 项目结构仍可继续按最新目录细化 | 后续维护统一以 README、AGENTS、architecture README、SKILL.md 为事实源 |
| 17 | 清理剩余冗余目录与重复文件：删除根目录重复 `init.sql`，将 `.cli/`、`.claude/` 从 Git 跟踪中移除但保留本地文件，并更新别名 Skill 中的初始化 SQL 路径说明 | `database/mysql-data/` 仍是本地 Docker 数据卷，`docs/reference/` 仍用于保留历史资料和用户要求保留的 SVG/PDF | 后续如需彻底瘦身，可决定是否归档或删除未被运行链路引用的历史参考文件 |
| 18 | 新增 Docker 开发热更新编排：`docker-compose.dev.yml` 挂载 `backend/`、`skills/`、`frontend/`，后端使用 `uvicorn --reload`，前端使用 Vite dev server，并修正文档中的 LLM 环境变量名 | 依赖文件、Dockerfile 和数据库初始化 SQL 变更仍需要重建镜像或重置数据卷；生产式本地运行与开发运行已使用不同项目名、容器名、端口和 MySQL 数据目录 | 后续开发可优先使用 `docker compose -f docker-compose.dev.yml up -d --build` 启动 |
| 19 | 将生产式 compose 与开发 compose 明确隔离：`chatbi-prod-*` 使用 5173/8000/3307 和 `database/mysql-data/`，`chatbi-dev-*` 使用 5174/8001/3308 和 `database/mysql-data-dev/` | 测试复用普通 compose；开发使用独立 `env.dev` | 如需切换 LLM 或数据库账号，可分别调整 `.env` 与 `env.dev` |
| 20 | 同步数据库目录命名：将原 `init_db/init.sql` 引用更新为 `database/init.sql`，并将 compose 数据卷统一放入 `database/mysql-data*` | `database/mysql-data*` 是运行数据目录，已加入 Git/Docker ignore；修改初始化 SQL 后仍需重置对应数据目录才会重放 | 后续数据库相关文件统一放在 `database/` 下维护 |
| 21 | 同步数据库运行数据目录命名：移除旧根目录 `mysql-data*` 忽略规则，保留并验证 `database/mysql-data*` 作为生产和开发数据卷目录 | 当前仅发现 `database/mysql-data/` 已存在，`database/mysql-data-dev/` 会在开发 compose 首次启动时创建 | 若之后改成更细的目录如 `database/data/prod`，需同步 compose、ignore 和 README |
| 22 | 收敛环境配置：删除多余 `.env.dev.example`、`.env.test.example` 和 `docker-compose.test.yml`，开发只保留本地 `env.dev`，测试复用普通 `docker-compose.yml` | `env.dev` 已加入 Git/Docker ignore；测试不再有独立端口和数据卷 | 后续只维护 `.env` 与 `env.dev` 两套本地环境变量 |
| 23 | 新增 `chatbi-file-ingestion` Skill：支持读取用户上传 CSV/XLSX，按 `sales_order` 与 `customer_profile` 表结构识别表头、校验类型并返回预览 JSON；补 CSV 单测 | 目前仅做文件读取与校验，不执行写库；前端尚未提供真实文件上传入口 | 下一步可补上传 API/前端控件，并设计显式导入到临时表或业务表的审批流程 |
| 24 | 新增 `/upload` 后端接口和聊天框文件入口：支持点击选择或拖拽 CSV/XLSX/XLSM，上传后自动生成带后端文件路径的校验消息草稿 | 当前上传后仍需用户点击发送触发 Skill；上传 API 测试在本机缺 FastAPI 时跳过，需 Docker 环境完整验证 | 重建 backend/frontend 容器后在浏览器拖入 `data/chatbi_sales.csv` 做端到端验证 |
| 25 | 新增 trace-id 链路日志：前端上传/聊天透传 `X-Trace-Id`，后端记录 upload、chat、planner、skill、SSE 节点到独立 `chatbi_logs.chatbi_trace_log`；BI 业务数据仍统一使用 `chatbi_demo` | 旧数据卷不会自动重放 `database/init.sql`，已在当前 dev MySQL 手动补建 `chatbi_logs` 授权；日志写入为 best-effort，不阻塞主链路 | 后续可加日志查询页面或按 trace-id 展示完整链路时间线 |
| 26 | 将日志库连接与业务库连接拆分：新增 `CHATBI_LOG_DB_HOST/PORT/USER/PASSWORD/NAME`，trace 写库优先使用日志库专用配置；dev/prod compose 不再硬编码日志库名，交给 env 注入 | `.env.dev` 可指向本机 MySQL，如 `host.docker.internal`；未配置日志库专用连接时仍回退到业务库连接以兼容现有 Docker dev | 配置本机日志库账号后重建 backend 容器，并用固定 trace-id 验证日志进入目标库 |
| 27 | 新增 `.envrc` 配置 direnv 项目级钩子：进入目录时加载 `.env`，再加载 `env.dev` 或 `.env.dev`，并加入本地 `.venv/bin` | 仍需要执行 `direnv allow` 信任本目录配置；shell 全局 hook 需用户 shell rc 已配置 | 执行 `direnv allow` 后重新进入目录，验证环境变量与虚拟环境 PATH 自动生效 |
| 28 | 执行 `direnv allow` 信任当前目录 `.envrc`，并验证 zsh 全局 hook 已在 `~/.zshrc` 配置 | 当前非交互命令环境不会持久加载 direnv 导出的变量；新开或重新进入交互式 zsh 后会自动生效 | 重新进入项目目录后用 `direnv status` 或 `echo $CHATBI_DB_PORT` 验证 |
| 29 | 修复 LiteLLM provider 配置：将 `.env` 的 `LLM_MODEL` 从 `ark/...` 调整为 `openai/...`，并在 `.env.example` 补充 ARK OpenAI-compatible 配置示例 | 运行中的 backend 进程/容器不会自动读取已修改的 `.env`，重启前端请求仍可能报 provider 错误 | 重启 backend（或对应 Docker 服务）后复测问答链路，确认不再出现 `LLM Provider NOT provided` |
| 30 | 明确 Agent 非 ReAct 的验收事实源：新增 `docs/design/agent-runtime-acceptance.md`、`docs/design/agent-react-evolution.md`，架构 README 链入；`tests/test_agent_runner_contract.py` 契约单测（单次 plan + 单次 skill） | 多步 ReAct 尚未开发，仅文档与设计约定 | 若产品上多 Skill 每轮，按 agent-react-evolution 实现 runner 循环 |
| 31 | 落地 ReAct runner：`react_runner` + `call_llm_for_react_step` + Observation 摘要回灌；`CHATBI_AGENT_REACT` / `CHATBI_AGENT_MAX_STEPS`；Legacy 路径保留；单测 `test_react_runner` / `test_observation` | 模型需遵守两轮 JSON（call_skill → finish）会增加一次 LLM 费用；`MAX_STEPS=1` 无法完成「工具+收尾」 | 联调时关注延迟与费用；勿将 `MAX_STEPS` 设为 1 |
| 32 | 修复图表空渲染容错：`plan_to_option` 在 LLM `chart_plan` 缺少 `dimension/metrics` 时自动从结果列推断并正常出图；补 `tests/test_chart_renderer.py` | 若数据列顺序与业务预期不一致，自动推断的维度可能不理想（默认首列为维度） | 后续可在 planner prompt 增加字段校验，优先输出完整 `chart_plan` 并附置信度 |
| 33 | 落地“Skill 决策，Tool 执行”图表链路：`chatbi-semantic-query` 脚本在 JSON 结果中输出 `chart_plan`（按问题语义自动选择 bar/line/pie 并给出维度与指标）；`stream_result_events` 优先使用 skill 返回的 `chart_plan` 调用 renderer；补协议单测验证优先级 | 当前 `chart_plan` 由单个语义查询技能内规则推断，尚未拆成独立 chart-planner Skill | 后续可新增 `chatbi-chart-planner` Skill 支持多轮 Observation 决策与置信度输出 |
| 34 | 在 legacy runner 新增多步 Skill 执行：`_build_steps` 识别”查询+建议”复合意图，自动组合 `chatbi-semantic-query` → `chatbi-decision-advisor` 双步执行；`_infer_primary_dimension` 将查询结果首列维度透传给决策建议；保留单步路径兼容其他问题类型 | 仅支持”查询+建议”固定双步组合，尚未泛化为任意多 Skill 链；决策意图正则以关键词为主，复杂歧义句可能误判 | 在前端验证”1-4月销售额排行并给出经营决策建议”触发双步，观察思考步骤中是否出现两段 thinking |
| 35 | 修复 SSE 事件重复渲染：`useChat.ts` 的 `setMessages` updater 直接 mutation `last` 对象，React 18 StrictMode 将 updater 调用两次导致 thinking/text 各追加两遍；改为每次在 updater 内用对象展开（`{...last, field: newVal}`）创建新对象，确保原始 `prev` 不被污染 | 仅影响开发环境（StrictMode）；生产构建不会触发此问题，但修复后开发环境调试体验一致 | 刷新页面后重发”查询+建议”消息，确认思考步骤不再逐条重复，内容区也不再整段复现 |
| 36 | 新增 `chatbi-comparison` Skill：支持按区域/渠道/产品类别等维度的月度环比分析；确定性脚本解析指标与维度，生成 CASE WHEN 双月 SQL，输出对比表格（Markdown）、分组柱状图 plan 和 KPI 环比卡片 | 仅支持 `sales_order` 表指标（销售额、毛利、毛利率、订单数、客户数、目标完成率），暂不覆盖 `customer_profile` 的留存率环比；月份解析默认取数据库最近两个月 | 在前端验证”各区域销售额环比”、”4月和3月毛利率对比”触发 `chatbi-comparison`，检查分组柱状图与 KPI 卡片是否正常渲染 |
| 37 | 落地会话持久化与管理中心 UI：`pymysql` 访问应用表、会话 REST、`/chat` 关联会话与数据源、`executor` 注入 DB；LLM 运行时合并 `llm_settings`；前端 Router + 四页管理；`skill_registry` 缺失表时 Runner 降级；文件上传单测 Windows 编码修复 | 已有数据卷需手动执行 `database/migrations/001_app_tables.sql` 或重建卷；管理 API 无鉴权（Demo） | 任务 7 端到端联调时在浏览器验证会话切换与管理页保存 |
| 38 | 修复 Docker 开发环境输入框不可用：前端 Vite 代理补齐 `/sessions` 与 `/admin`，并为 backend 补充 `cryptography` 依赖以兼容 MySQL8 `caching_sha2_password`；重建 backend 后 `/sessions` 经前端域名返回 200 JSON | 这是开发编排链路问题（代理 + 依赖），非前端输入组件本身逻辑缺陷 | 浏览器刷新 `http://localhost:5174`，确认输入框可聚焦并可发送消息 |
| 39 | 新增“当前使用中”展示：`/admin/db-connections/current` 返回当前生效数据库连接（默认连接优先，缺省回退 env），`/admin/llm-settings` 增加 `effective_*` 字段；前端数据源页与 LLM 页顶部展示当前生效配置 | 当前仅展示“技能脚本使用”的数据库来源与“LiteLLM 实际参数来源”，未按会话级 `db_connection_id` 做实时覆盖展示 | 刷新管理页验证：数据源页显示当前连接摘要，LLM 页显示当前生效模型/API Base/API Key 状态 |
| 40 | 会话标题改为随聊天内容动态更新：`POST /chat` 在落库用户消息后，每轮都按最新问题生成并写入 `chat_session.title`（空白折叠、去换行、80 字截断） | 若用户希望“手工重命名后不再自动覆盖”，当前逻辑尚未区分该场景 | 发送多轮消息并观察左侧会话列表，标题应始终跟随最近一次用户输入 |
| 41 | 聊天输入区视觉优化：`ChatInput` 改为更圆润风格（外层 `rounded-2xl`，按钮与输入框 `rounded-full`，统一高度与留白）以匹配整体页面气质 | 当前仅调整输入区组件样式，未改全局色板与阴影体系 | 刷新聊天页确认输入区不再“方块感”，交互功能保持不变 |
| 42 | 在 PR 分支 `dev03/memoryAndFrontend` 合并 `origin/main` 并解决冲突：保留 ReAct/会话数据源覆盖、多步查询建议、SSE 不可变更新和文件导入测试；同时保留 `chatbi-comparison` 迭代记录 | 尚需本机执行 `git add`、`git commit`、`git push origin dev03/memoryAndFrontend` 完成 PR 分支更新 | 推送 PR 分支后刷新 GitHub PR，确认冲突提示消失 |
| 43 | 完成任务 10：应用用户表 + JWT + 用户管理页 + `user_memory` 与会话归属；Agent 注入记忆块与异步摘要；旧库需执行 `002` 迁移或重建数据卷 | `tests/test_agent_workflow.py` 等仍因历史 `build_execution_steps` 导入错误无法收集；与本任务无关，需单独修复或移除过时导入 | 旧环境执行 `database/migrations/002_users_and_memory.sql`；浏览器用 admin 登录验证会话隔离与记忆 chip；可选修复失效测试文件导入 |
| 44 | 将 `chatbi-decision-advisor` 改为按问题中的指标/维度定向生成建议：拆分脚本为 `decision_advisor_core.py` + 轻量入口，新增 `focus_metrics` 解析，建议规则按指标与维度过滤；补充 `test_decision_advisor_focus` 覆盖毛利率定向建议，并修正 `test_query_advice_dimension_flow` 的轻量依赖 stub | 本机当前无法连接 `127.0.0.1:3307`，未完成真实数据库场景回归；若问题未显式包含指标或维度，技能仍会返回综合经营建议 | 启动/连通本地 MySQL 后复测 `各渠道毛利率经营建议`、`华东销售额经营建议`、`客户留存经营建议`，确认建议主题随数据需求变化 |
| 45 | 增强 trace-id 日志链路：`database/init.sql` 初始化即创建 `chatbi_logs.chatbi_trace_log`；新增 `skills/_shared/trace.py` 供 Skill 子进程复用同一日志表；`agent.skill completed` 事件增加 `skill_result_log_payload` 结果摘要（如 row 数、Query Intent 状态、metric/dimension IDs、advice 数） | 当前仅补齐了日志基础设施与 Agent 结果摘要；具体某个新 Skill 若要记录更细颗粒度的内部步骤，还需在对应脚本里显式调用 `log_skill_event(...)` | 后续给新 Skill 脚本接入 `log_skill_event(started/completed/failed)`，并用 trace_id 在 `chatbi_trace_log` 中串起 HTTP → planner → skill → memory 全链路 |
| 46 | 开发环境可关闭用户登录：`CHATBI_AUTH_ENABLED` / `VITE_AUTH_ENABLED`（未设置视为开启以保护生产）；`docker-compose.dev.yml` 默认关闭；免登录时优先使用种子 `admin`（`CHATBI_AUTH_DEV_USER_ID` 为管理员时仍用该 id；否则回退到 `admin` 用户）；将 `chatbi-decision-advisor` 改为按问题中的指标/维度定向生成建议：拆分脚本为 `decision_advisor_core.py` + 轻量入口，新增 `focus_metrics` 解析，建议规则按指标与维度过滤，并补充 `test_decision_advisor_focus` 等 | 本机全量 `pytest` 仍会因 Windows 下误收集 `database/mysql-data*`、以及过时 runner 导入报错（既有问题）；同时当前本机无法连接 `127.0.0.1:3307`，未完成真实数据库场景回归 | 开发容器内需前后端开关一致并本地同步 `.env`/`env.dev` 两处变量；启动/连通本地 MySQL 后复测 `各渠道毛利率经营建议`、`华东销售额经营建议`、`客户留存经营建议`，确认建议主题随数据需求变化 |
| 47 | 补齐前端用户行为与管理行为日志：`/auth/login`、`/admin/users`、`/sessions`、`/admin/db-connections` 相关接口均接入 `request_trace_id` + `log_event`，记录登录成功/失败、用户创建/修改/禁用、会话创建/重命名/删除、数据源连接 CRUD/测试等行为 | 当前尚未覆盖 `admin_llm_route`、`admin_skills_route`、`auth/me` 等次级管理接口；如果需要完整审计，还可继续扩展 | 在前端分别执行登录、建用户、禁用用户、新建会话、重命名会话、创建数据源连接后，到 `chatbi_logs.chatbi_trace_log` 按 trace_id 查询对应事件 |
| 48 | 继续补齐剩余前端入口日志：`/admin/llm-settings`、`/admin/skills`、`/dashboard/overview`、`/auth/me` 也已接入 `request_trace_id` + `log_event`；当前 `backend/routes` 下除 `__init__.py` 外均具备 trace 入口 | 路由级别已基本全覆盖，但某些业务内部异常分支仍可能只依赖统一异常返回，未必都有专门事件名；若要更细粒度审计，可继续细分失败原因与字段脱敏策略 | 在前端依次访问管理页、技能页、dashboard、个人信息接口，并在 `chatbi_trace_log` 中确认新增的 `admin.llm_settings`、`admin.skills`、`dashboard.overview`、`auth.me` 事件 |
| 49 | 重建 `skills/chatbi-semantic-processing`：补回 `scripts/semantic_process.py` + `semantic_processing_core.py`，让当前 Agent 可直接执行并返回标准 `query_intent`；同时补 `tests/test_semantic_processing_skill.py` 覆盖 ready/clarification/trend 三类语义解析输出 | 当前实现为确定性规则版，优先满足 Agent 调度与审计日志契约；尚未接入真实银行 schema 元数据或更细粒度过滤值抽取 | 用 `python -m pytest tests/test_semantic_processing_skill.py tests/test_skill_result_log_payload.py` 验证输出契约；后续如需要可继续补 business filter、comparison period 和 schema hints 细节 |
| 50 | 完成任务 11：Multi-Agent 编排（registry + 路由 + 专线过滤 Skill + 汇总）、图像上传与 Vision 抽取注入、`GET /sessions/{id}/report.pdf`、前端开关与 PDF 按钮；补充单测；backend Dockerfile 增加 WeasyPrint 系统依赖 | `tests/test_agent_workflow.py` 仍引用已删除符号无法收集；无 GTK 的 Windows 主机上 WeasyPrint PDF 生成会 RuntimeError，PDF 单测降级为跳过 | 重建 backend 镜像后验证 PDF；配置支持 vision 的 LLM；按需修复或移除过时 `test_agent_workflow` |
| 51 | 修复 PDF 导出 500：`render_session_pdf_bytes` 增加降级链路（WeasyPrint 失败自动回退 ReportLab），并补充 `test_render_session_pdf_bytes_fallback_to_reportlab`；`requirements.txt` 新增 `reportlab` 依赖 | 回退链路为文本型 PDF（可读但不含 HTML 样式）；若要与 WeasyPrint 视觉一致仍建议在容器安装 Cairo/Pango | 重建 backend 依赖后在前端点击“导出 PDF 报告”验证，确认 Windows/本机环境不再 500 |
| 52 | 修复开发镜像构建失败：`backend/Dockerfile` 将 Debian 不可用包 `libgdk-pixbuf2.0-0` 改为可用包名 `libgdk-pixbuf-2.0-0`，消除 `apt-get install` exit code 100 | 若基础镜像后续继续升级，系统包名仍可能变化；建议锁定基础镜像 digest 或在 CI 增加定期构建探测 | 重新执行 `docker compose --env-file .env.dev -f docker-compose.dev.yml up -d --build` 验证 backend 构建通过 |
| 53 | 修复 PDF 图表中文乱码：`backend/report/pdf_chart_png.py` 增加运行时字体探测与 CJK 字体优先策略，`matplotlib` 优先使用可用中文字体再回退 DejaVu；补单测 `test_select_sans_fonts_prefers_cjk` | 若运行环境缺少任何 CJK 字体，仍会回退到 DejaVu，中文可能继续显示异常 | 在目标环境安装 Noto/微软雅黑等中文字体并重启后端，重新导出 PDF 验证图表标题和坐标轴中文显示正常 |
| 54 | 修复 Agent 两类体验问题：`/chat` SSE 在前端切页断连后改为“继续后端执行、仅停止推流”避免任务中断；新增 `backend/agent/intent_guard.py` 对简短寒暄/致谢进行直答短路，legacy 与 ReAct 均跳过不必要 Skill 调用；补充 `test_chat_route_disconnect`、`test_react_runner`、`test_agent_runner_contract` 覆盖 | `intent_guard` 当前是规则式判定，覆盖常见简单话语但非完整对话意图分类；复杂混合句仍由原 planner/LLM 处理 | 前端复测：发送查询后立即切换页面再切回，确认最终消息能落库显示；连续多轮后输入“你好/谢谢”应直接回复且 trace 中不出现 `agent.skill.started` |
| 55 | 适配 `skills/chatbi-chart-recommendation` 到当前框架：补回 `scripts/recommend_chart.py` + `chart_recommendation_core.py`，输出当前 Agent 可消费的 `charts/kpis`，并为“推荐什么图表/如何可视化”补一条 planner 触发规则 | 当前版本默认优先吃 JSON 输入 `{question, rows}`；如果只有自然语言问题而没有结果行，会返回 `need_clarification`，尚未自动串到查询后置链路 | 用 `env PYTHONPATH=. python3 tests/test_chart_recommendation_skill.py tests/test_agent_skill_protocol.py` 验证；前端可通过技能直调或后续接入 query 后置链路验证图表渲染 |
| 56 | 适配 `skills/chatbi-dashboard-orchestration` 到当前框架：补回 `scripts/orchestrate_dashboard.py` + `dashboard_orchestration_core.py`，让技能可直接消费 dashboard overview 数据并返回 `dashboard_spec + charts + kpis`；同时为“生成看板/仪表盘编排”补 planner 触发规则 | 当前版本优先吃现有 `/dashboard/overview` 的数据形状；尚未真正接管前端 `/dashboard` 页面，也未自动串联 query/chart recommendation 的多技能结果 | 用 `env PYTHONPATH=. python3 tests/test_dashboard_orchestration_skill.py tests/test_agent_skill_protocol.py` 验证；后续如需要可再把 dashboard 页面改成消费 `dashboard_spec` |
| 57 | 适配 `skills/chatbi-chart-recommendation` 到当前框架：补回 `scripts/recommend_chart.py` + `chart_recommendation_core.py`，输出当前 Agent 可消费的 `charts/kpis`，并为“推荐什么图表/如何可视化”补一条 planner 触发规则 | 当前版本默认优先吃 JSON 输入 `{question, rows}`；如果只有自然语言问题而没有结果行，会返回 `need_clarification`，尚未自动串到查询后置链路 | 用 `env PYTHONPATH=. python3 tests/test_chart_recommendation_skill.py tests/test_agent_skill_protocol.py` 验证；前端可通过技能直调或后续接入 query 后置链路验证图表渲染 |
| 58 | 适配 `skills/chatbi-dashboard-orchestration` 到当前框架：补回 `scripts/orchestrate_dashboard.py` + `dashboard_orchestration_core.py`，让技能可直接消费 dashboard overview 数据并返回 `dashboard_spec + charts + kpis`；同时为“生成看板/仪表盘编排”补 planner 触发规则 | 当前版本优先吃现有 `/dashboard/overview` 的数据形状；尚未真正接管前端 `/dashboard` 页面，也未自动串联 query/chart recommendation 的多技能结果 | 用 `env PYTHONPATH=. python3 tests/test_dashboard_orchestration_skill.py tests/test_agent_skill_protocol.py` 验证；后续如需要可再把 dashboard 页面改成消费 `dashboard_spec` |
| 59 | 统一测试环境优先级：新增 `backend/env_loader.py`，运行时按 `.env` → `.env.dev` → `env.dev` 顺序加载，让本地测试默认优先走 dev 数据库；同时将“测试优先使用项目内 `.venv`、优先读取 `.env.dev`、包导入测试优先用 `PYTHONPATH=. .venv/bin/python -m pytest`”写入 `AGENTS.md` 作为项目约定 | 当前若手工直接写 `python3 -m pytest`，解释器仍取决于调用者 shell；约定层面已统一，但执行时仍应显式使用 `.venv/bin/python` | 用 `PYTHONPATH=. .venv/bin/python -m pytest tests/test_env_loader.py` 验证 `.env.dev` 覆盖 `.env`，并确认测试进程解释器来自项目内 `.venv` |
| 60 | 为当前 Python 依赖补齐 `pytest`：`requirements.txt` 新增 `pytest>=8,<9`，便于项目内 `.venv` 直接使用 `-m pytest` 跑测试 | 当前仅补齐依赖声明；若本地 `.venv` 尚未重新安装依赖，`pytest` 模块仍不会立即出现 | 执行 `.venv/bin/python -m pip install -r requirements.txt` 后，用 `PYTHONPATH=. .venv/bin/python -m pytest tests/test_env_loader.py` 验证 |
| 61 | 完成任务 12：管理员 `GET/PUT /admin/multi-agents` + 前端「多Agents管理」页与 Vitest/Pytest | 无 | 管理员账号下打开 `/multi-agents` 保存后确认 `skills/_agents/registry.yaml` 与多专线对话行为一致 |
| 62 | 修复上传 CSV 后轮对话丢失上下文：`upload_context` 从会话中提取 `/tmp/chatbi-uploads/` 路径并在跟进回合注入提示；System/ReAct prompt 明确「上传文件优先于 semantic-query」 | 无 | 浏览器：首轮上传校验后轮「分析 CSV 并画图」应走 `chatbi-file-ingestion --include-rows`，而非演示库查询 |
| 63 | 修复导航离开对话页再返回时会话与助手消息「丢失」：`sessionStorage` 持久化当前 `session_id`，挂载时用 `resolveInitialSessionId` 恢复选中会话（不再无脑 `list[0]`）；`useChat` 在消息末尾为 `user`（后端仍在生成、助手尚未落库）时轮询 `GET /sessions/:id/messages` 直至出现助手消息；`assistantPending` + `AssistantPendingNotice` + 输入区「处理中」避免空白等待感；轮询间隔 1s | 轮询最长约 3 分钟（180×1s）；极端长时间生成仍会停止轮询 | 浏览器：在非第一条会话中提问 → 切到仪表盘再回对话，仍应保持同一会话；应立刻看到「助手正在生成回复」提示直至内容出现 |
| 64 | 新增本地外部银行数据库测试资产：`database/external_bank_*.sql` 初始化 `chatbi_bank_external`，覆盖网点、客户、账户、存款、贷款、还款、银行卡、渠道交易、财富持仓、风险事件，并提供 `sales_order` / `customer_profile` 兼容视图和语义层元数据 | 当前宿主机 `3306` 已有 MySQL 监听，但 `root` 需要密码且 `demo_user/demo_pass` 尚无权限，未能由 Agent 直接导入 | 用本机 root 凭据在 `3306` 导入 SQL 后，在前端数据源管理新增 Host=`host.docker.internal`、Port=`3306`、Database=`chatbi_bank_external` 的连接并设为默认 |
| 65 | 新增 `chatbi-database-overview` Skill：读取当前生效业务库的 `information_schema` 与 ChatBI 语义层，返回可查询业务表/视图、字段、行数、指标、维度和推荐提问；Agent prompt 增加“数据库概览/表清单/schema”触发规则，并加入分析专线白名单 | 已通过脚本单测与 dev backend 容器真实调用；`test_agent_runner_contract.py` 在当前本机 `.venv` 缺 `pymysql`，仍无法作为本轮验证项收集 | 前端提问“当前数据库有哪些表可以查”验证是否稳定选择 `chatbi-database-overview`；必要时再补 deterministic router 规则 |
| 66 | 新增用户向技术与使用文档 `docs/user-guide.md`：产品能力、启动方式概要、登录与角色、各路由页面功能、对话区与会话/上传/PDF/多专线、仪表盘与各管理页说明、典型问法与限制 | 无 | 后续若路由或菜单变更，同步更新该文档 |
| 67 | 新增开发者向 `docs/tech-guide.md`：单 Agent（ReAct/Legacy）与 Multi-Agent 编排、System/User 消息拼装、记忆读写、四库表职责、上传路径与 Skill 调用、各 Skill 职责表 | 无 | Agent 或 registry 行为变更时同步更新 |
| 68 | 搭建当前功能模块自动化测试框架：新增 `scripts/run_tests.py`，按 `foundation/skills/agent/admin/auth-memory/dashboard/data-sources/upload-vision/report` 分套件执行，保留 `quick/backend/auth/data` 别名；新增 `tests/README.md` 与 `test_run_tests_script.py` 自检，确保所有 `tests/test_*.py` 归属模块套件 | 当前仍保留原有扁平 `tests/` 目录，先解决执行入口和模块归属；尚未物理迁移测试文件到子目录 | 日常用 `PYTHONPATH=. .venv/bin/python scripts/run_tests.py quick -- -q`；后续如需要再按套件逐步迁移到 `tests/<module>/` |
| 69 | 补充自动化测试框架正式文档：新增 `docs/testing/README.md`，说明统一入口、模块套件、别名、新增测试规则和后续目录迁移方向；同步 `AGENTS.md` 快速导航与测试规则、`docs/conventions/README.md` 测试规范，`tests/README.md` 改为指向正式文档 | 当前文档已统一入口；测试文件仍未物理迁移，继续由 `scripts/run_tests.py` 维护模块归属 | 后续新增测试时先更新 `MODULE_SUITES`，再跑 `PYTHONPATH=. .venv/bin/python scripts/run_tests.py quick -- -q` |
| 70 | 修复全量测试收集与执行：`tests/test_agent_workflow.py` 对齐当前 runner 的 `_build_steps` / `_is_query_plus_decision` 与 prompt 触发规则，移除旧 `build_execution_steps` / deterministic override 依赖；`test_skill_registry_graceful.py` patch 当前 `admin_fetch_all`；`scripts/run_tests.py all -- -q` 现为 83 passed | 全量仍有第三方库 warning：passlib `crypt` deprecation、测试 JWT secret 太短的 PyJWT warning；不影响当前功能 | 后续可单独收敛 warning：给测试 JWT 使用 32+ bytes secret，并跟进 passlib/Python 3.13 兼容 |
| 71 | 将具体测试用例索引写入 `docs/testing/README.md`：按 Foundation、Skills、Agent、Admin/Auth/Memory、Dashboard/Data Sources、Upload/Vision/Report 汇总 83 个 pytest 用例的保护目标，并保留 collect-only 命令用于查看精确节点名 | 文档为用例索引和保护目标说明，不替代 pytest 收集结果；新增/重命名测试时需同步更新 | 后续新增测试时同时更新 `MODULE_SUITES` 与 `docs/testing/README.md` 的用例索引 |
| 72 | 新增 GitHub Actions CI：`.github/workflows/ci.yml` 在 PR 到 `main`、push 到 `main`、手动触发时自动跑后端 `python scripts/run_tests.py all -- -q` 与前端 `npm run lint/test/build`；新增 `docs/ci-cd/README.md` 说明触发条件、本地提交前命令和 CD 预留策略，并在 `AGENTS.md` 增加导航；顺手修复前端 lint 历史问题（拆分 `useAuth`，避免 effect 同步 setState） | 本地已验证后端 83 passed、前端 lint/Vitest/build 通过；build 仍提示 bundle chunk 超 500k 的 Vite warning，不阻塞 CI；同事任意命名分支只要提 PR 到 main 即触发 | 推送到 GitHub 后查看 Actions 首跑结果；后续可按需给前端做代码分割降低 chunk size |
| 73 | 复核并加固 E2E smoke：`scripts/e2e_smoke.py` 直接请求 `/chat` SSE，覆盖典型问数、数据库概览、对比、多步建议、指标口径解释、图表 JSON 泄漏和小聊天不调 Skill；补充 HTTP/超时/done 校验、文本断言、非 TTY 输出、`CHATBI_E2E_URL/TOKEN` 环境变量和未知用例校验；`docs/testing/e2e-manual.md` 修正外部库 SQL 路径并在测试文档链接 E2E 清单 | E2E smoke 依赖后端、数据库和 LLM 在线，暂不进入默认 GitHub Actions；`S2/M1/M2` 已定位为 ReAct 收尾 JSON 脆弱和查询+建议补跑不稳定，并补单测保护 | 后端/LLM 启动后用 `python scripts/e2e_smoke.py --cases S1,S4,E1` 做最小烟雾，再按需跑全量 |
| 74 | 加固 ReAct 查询+建议链路：抽出 `backend/agent/query_decision.py` 统一判断复合意图，`react_runner` 在 semantic-query 后自动补跑 `chatbi-decision-advisor`，并在模型 finish JSON 异常时回退展示最后一次 Skill 结果；新增 `test_e2e_smoke_script.py` 与 ReAct 单测覆盖 smoke 文本断言、自动补跑和收尾异常兜底 | 未继续跑全量 E2E，按用户要求由本地自行验证；当前只补代码与单元保护 | 用户本地复跑 `python scripts/e2e_smoke.py --cases S2,M1,M2,S6`，确认烟雾链路稳定 |
| 75 | 修复 GitHub Actions Python 格式检查失败：`backend/agent/query_decision.py`、`scripts/e2e_smoke.py`、`tests/test_e2e_smoke_script.py`、`tests/test_react_runner.py` 统一按 `black` 重排，消除 `black --check backend/ scripts/ tests/` 的 4 个格式差异 | 本次失败是格式问题，不是 `ruff` 或业务测试回归；若后续再次出现同类报错，优先本地跑 `ruff check` 和 `black --check` | 提交前执行 `PYTHONPATH=. .venv/bin/python -m black --check backend/ scripts/ tests/` 与 `PYTHONPATH=. .venv/bin/python -m ruff check backend/ scripts/ tests/` |
| 76 | 对话页欢迎态：无消息时会话主区垂直居中展示「有什么可以帮到你？」+ `ChatComposerDock`；首条消息发送后恢复底部输入区；侧栏 `ChatSessionSidebar`；`chatWelcomeView` + Vitest；后续已按产品要求移除 Logo 与 `@logo` 别名 | 无 | 浏览器验证新对话 → 发送一条 →「新对话」回到欢迎态 |
| 77 | 修复上传文件校验偶发“文件不存在”：`backend/agent/executor.py` 在执行 `chatbi-file-ingestion` 前强制从参数/会话用户消息提取规范化 `/tmp/chatbi-uploads/...` 路径并保留 `--include-rows` 等选项，避免 LLM 把整句或带标点路径直接传给脚本；`upload_context` 只从 user 消息提取主路径，避免被 assistant 失败回显污染 | 该修复主要消除“路径提取不稳”导致的偶发失败；尚未在浏览器做完整手工回归（点击附件 vs 拖拽） | 浏览器分别用“点击附件”和“拖拽”上传同一 CSV 连续验证，确认都稳定走 `chatbi-file-ingestion` 且不再报文件不存在 |
| 78 | 修复 KPI 卡片重复同值：`backend/renderers/kpi.py` 移除“单行数据自动取首个数值字段”的兜底逻辑，避免在 `field` 不匹配时把同一数值填入多张 KPI 卡片；新增 `tests/test_kpi_renderer.py` 覆盖字段不匹配与精确匹配两种场景 | 当前策略为“字段匹配不到即使用 default”，不会再猜测映射；若后续想更智能映射，建议在 skill 侧输出明确字段名 | 在前端复测上传文件分析，确认 KPI 卡片不再全部显示同一个值；必要时让对应 skill 输出与卡片 `field` 一致的列名 |
| 79 | 修复聊天内容原样显示 Markdown 标记：新增 `frontend/src/lib/inlineMarkdown.ts`，将行内 `**...**` 解析为加粗 token；`MessageBubble` 渲染普通行、标题和列表时统一走行内解析，并支持 `•` 列表符 | 当前为轻量行内解析，仅处理 `**bold**`，不包含完整 Markdown 语法（如链接、表格） | 前端发送包含 `**时间范围**`、`• **区域**` 的消息，确认展示为加粗文本而非原始 `**` 标记 |
| 80 | 修复表格内容仍以 Markdown 文本显示：新增 `frontend/src/lib/markdownBlocks.ts` 识别 `|...|` + 分隔行语法并解析为结构化表格块；`MessageBubble` 在 `FormattedContent` 中将表格块渲染为真实 `<table>`，普通段落/列表逻辑保持不变 | 当前仅覆盖标准 Markdown 表格写法（首尾 `|` + 分隔行），未扩展到更宽松语法变体 | 在前端复测包含区域销售分析的表格输出，确认头部和行数据以真实表格展示而非 `|` 文本 |
| 81 | 增强 LLM 配置页可用性：新增 `llmConfigValidation` 规则与提示文案，在管理页实时展示 LiteLLM 配置提醒，并在保存前阻止不合法组合（OpenAI 兼容 `API Base` + 非 `openai/` 模型名）；新增 `llmConfigValidation.test.ts` 覆盖关键规则 | 当前按常见 OpenAI 兼容网关域名判定（含 minimaxi/openai 等）；若后续接入新的兼容域名需补充白名单 | 在管理页填写 `API Base=https://api.minimaxi.com/v1` 且 `model=gpt-4o-mini`，应看到错误并禁用保存；改为 `openai/gpt-4o-mini` 后恢复可保存 |
| 82 | LLM 配置页新增厂商快捷配置按钮：`LlmConfigPage` 增加 OpenAI / Anthropic / ARK / MiniMax 预设胶囊按钮，点击后自动填充模型名与 API Base（API Key 继续手输）；新增 `llmProviderPresets` 与单测 | 当前预设是常用默认值，后续若厂商默认模型升级需同步调整预设映射 | 在 LLM 配置页点击任一厂商按钮，确认模型/API Base 自动填充、高亮当前预设，并可直接输入 API Key 后保存 |
| 83 | LLM 配置页补充厂商说明区：根据当前命中的预设展示动态“推荐配置说明”（模型前缀规则 + 网关注意事项）；未命中预设时展示灰色引导文案，提示先选厂商按钮再填 API Key | 说明区基于当前预设元数据，若后续新增厂商需要同步补充 `modelRule/note` 文案 | 手动切换 OpenAI/Anthropic/ARK/MiniMax 按钮，确认说明区随选项切换；手工改成非预设组合时显示“未命中预设”提示 |
| 84 | 补充 DeepSeek 厂商预设：`llmProviderPresets` 新增 DeepSeek（`openai/deepseek-v4-flash` + `https://api.deepseek.com`）并纳入说明区；同时将 `deepseek.com` 纳入 OpenAI 兼容网关校验，确保非 `openai/` 模型名会被阻止保存；补对应单测 | DeepSeek 模型版本迭代较快，后续若默认推荐模型变更需同步更新预设值 | 在 LLM 配置页点击 DeepSeek，确认模型/API Base 自动填充；改成不带 `openai/` 的模型名应出现错误，改回 `openai/deepseek-v4-flash` 可保存 |
| 85 | 收紧 Agent 测试执行规则：`AGENTS.md`、`docs/testing/README.md`、`docs/conventions/README.md` 明确要求 Agent 每次完成代码或测试改动后必须至少跑一遍 `scripts/run_tests.py` 对应套件；若新增 `tests/test_*.py`，必须先注册到 `scripts/run_tests.py` 的 `MODULE_SUITES` 再做本地测试 | 当前约束落在文档与入口规则，仍依赖 `test_run_tests_script.py` 作为 CI 兜底；尚未实现自动补全 suite | 后续如需进一步防漏，可在 `scripts/run_tests.py` 增加未归类测试提示或建议归类输出 |
| 86 | 补登记遗漏测试到模块套件：将 `test_executor_file_ingestion_args.py`、`test_kpi_renderer.py`、`test_memory_repo_prompts.py` 分别纳入 `data-sources`、`dashboard`、`auth-memory`，并同步 `docs/testing/README.md` 用例索引，修复 `test_run_tests_script.py` 因未归类测试失败的问题 | 当前仅补 suite 登记与文档，不改测试内容本身；若后续再新增测试文件，仍需同步维护 `MODULE_SUITES` | 本地执行 `PYTHONPATH=. .venv/bin/python scripts/run_tests.py quick -- -q` 与 `... scripts/run_tests.py all -- -q`，确认测试入口恢复为绿 |
| 87 | 拆分 `chatbi-semantic-query` Skill：将 672 行单文件脚本重构为 `semantic_query/` 包，按 `models / metadata / parsing / planner / sql_builder / presenters / chart_html / entry` 拆分职责；新增 `test_semantic_query_core.py` 直接覆盖 plan 构建与图表计划输出，并登记到 `scripts/run_tests.py` 的 `skills` 套件 | 本次以结构重构为主，保持现有 SQL 与 JSON 输出兼容；单值 KPI、`NULL` 空结果和 `.env.dev` 默认端口一致性仍可在后续单独增强 | 本地执行 `PYTHONPATH=. .venv/bin/python scripts/run_tests.py quick -- -q`、`ruff check`、`black --check`，并用 `./.venv/bin/python skills/chatbi-semantic-query/scripts/chatbi_semantic_query.py "...\" --json --show-sql --port 3308` 回归典型问句 |
| 88 | 增强 `chatbi-semantic-query` 输出层：`presenters.py` 对单值指标自动产出 `kpis`，比率类指标统一格式化为百分比文本/单位；聚合查询返回单行 `NULL` 时改为“未返回数据”空态；补 `test_semantic_query_core.py` 覆盖单值 KPI 与空结果场景 | 当前仅按字段名中的“率/占比/比例/份额”判断百分比指标，未结合语义层口径表做更精细单位映射 | 本地执行 `PYTHONPATH=. .venv/bin/python scripts/run_tests.py quick -- -q`，并回归 `华东4月毛利率`、`2024年销售额`，确认分别输出 KPI 百分比与友好空态 |
| 89 | 收紧 `chatbi-semantic-query` 维度词典策略：`parsing.py` 将维度近义词改为“`alias_mapping` 优先 + 极薄代码 fallback”，把 `DIMENSION_SYNONYMS` 缩减为仅保留 `各区域`、`按月`、`趋势`、`来源渠道` 等通用语言兜底词；补 `test_semantic_query_core.py` 覆盖数据库别名 `大区 -> 区域` 与 fallback 词 `按月 -> 月份` | 仍保留少量代码兜底词，避免完全依赖元数据后让通用中文表达退化；若后续业务词继续增长，优先走 `chatbi-alias-manager` 写入 `alias_mapping` 而不是继续堆硬编码 | 本地执行 `PYTHONPATH=. .venv/bin/python scripts/run_tests.py quick -- -q`，并回归 `1-4月大区收入排行`、`销售额按月趋势`，确认 DB alias 与 fallback 两条链路都可用 |
| 90 | 为 `chatbi-semantic-query` 增加可展示查询计划：`presenters.py` 新增 `plan_summary` 序列化，将指标、维度、过滤、时间条件、排序和 limit 挂到 JSON 输出的 `data.plan_summary`；主入口在 `--json` 模式透传 `SemanticPlan`；补 `test_semantic_query_core.py` 覆盖 summary 结构 | 当前 `time_filter` 仍直接暴露 SQL 条件字符串，适合调试但不算最终用户友好的自然语言展示；如前端要正式展示，可后续再补 `time_scope_label` 一类字段 | 本地执行 `PYTHONPATH=. .venv/bin/python scripts/run_tests.py quick -- -q`，并回归 `1-4月各区域销售额排行 --json --show-sql --port 3308`，确认返回 `data.plan_summary` |
| 91 | 打通 `plan_summary` 到前端消息链路：后端 `formatter.py` 新增 `plan_summary` SSE 事件，`chat_route.py` 将其持久化到 assistant payload；前端 `useChat` / `types/message.ts` 接收该字段，供后续调试或扩展使用 | 当前页面不再单独渲染“查询计划”卡片，避免与思考步骤重复；历史消息没有该字段，需重新发起新问句才能看到最新计划说明 | 本地执行 `PYTHONPATH=. .venv/bin/python scripts/run_tests.py quick -- -q` 与 `cd frontend && npm run build`，然后在对话页重新发送问数消息确认链路正常 |
| 92 | 将查询计划细化为多条实时思考轨迹：`presenters.py` 基于 `SemanticPlan` 生成 `plan_trace`（收到问题、识别时间、指标、维度、过滤、排序、SQL），`backend/agent/formatter.py` 将其逐条转成 `thinking` 事件；保留 `plan_summary` 供链路和持久化使用，但页面不再单独渲染计划卡片 | 当前思考步骤里仍包含 SQL 条件串，偏调试展示；若后续需要更业务友好的说明，可再把时间/排序改成自然语言标签 | 本地执行 `PYTHONPATH=. .venv/bin/python scripts/run_tests.py quick -- -q`，刷新页面后新发一条问数消息，确认“思考步骤”里按顺序展示多条查询计划轨迹 |
| 93 | 修复 `chatbi-semantic-query` 多指标歧义选错指标：`pick_metric` 从“仅按词长匹配”升级为“优先比率类指标，其次优先更靠后命中的词，再看词长”，使 `2-4月销售额毛利率排行` 这类问法优先落到 `毛利率`；补 `test_semantic_query_core.py` 覆盖多指标命中场景并用真库回归 SQL | 当前仍只支持单一主指标；若一句话同时明确要求多个指标（如“销售额和毛利率对比”），后续仍应考虑澄清或多指标查询能力 | 本地执行 `PYTHONPATH=. .venv/bin/python scripts/run_tests.py quick -- -q`，并回归 `./.venv/bin/python skills/chatbi-semantic-query/scripts/chatbi_semantic_query.py "2-4月销售额毛利率排行" --json --show-sql --port 3308`，确认 SQL 改为按 `毛利率` 排序 |
| 94 | 修复 GitHub Actions Python 格式检查失败：`backend/agent/formatter.py`、`tests/test_agent_skill_protocol.py`、`tests/test_semantic_query_core.py` 按 `black` 统一重排，消除 CI 中 `black --check backend/ scripts/ tests/` 的 3 处格式差异；确认 `ruff check` 本身并未报错 | 本次是纯格式修复，不涉及业务逻辑变化；若后续 CI 再出现 `would reformat ...`，优先本地执行 `black --check` 或直接对目标文件跑 `black` | 本地执行 `PYTHONPATH=. .venv/bin/python scripts/run_tests.py foundation skills agent -- -q`，并复跑 `PYTHONPATH=. .venv/bin/python -m black --check backend/ scripts/ tests/` 确认恢复为绿 |
| 95 | 修复开发容器 backend 构建时 `pip` 访问清华源 SSL EOF 失败：`backend/Dockerfile` 改为 `ARG PIP_INDEX_URL=https://pypi.org/simple` + `pip install --index-url ${PIP_INDEX_URL}`，默认走官方 PyPI，同时保留通过 `--build-arg` 覆盖镜像源的能力 | 当前只修复 backend 构建源配置，不处理宿主机 Docker/WSL 代理本身；若外网仍受限，可在构建命令里显式传入可用镜像源 | 本地执行 `docker compose -f docker-compose.dev.yml config` 与 `PYTHONPATH=. .venv/bin/python scripts/run_tests.py foundation -- -q`；重建时使用 `docker compose --env-file .env.dev -f docker-compose.dev.yml up -d --build`，如需镜像源可加 `--build-arg PIP_INDEX_URL=...` |
| 96 | LLM 多档案与 Fallback：`llm_model_profile` + `active_profile_id`；管理 API CRUD/排序/选用/检测；`chatbi_acompletion`/`chatbi_completion` 链式 fallback；LLM 配置页右侧列表与 Vitest `llmProfileUi` / Pytest 档案与 fallback 单测；`discover_python_tests` Windows 路径归一 | 旧库需执行 `database/migrations/004_llm_model_profiles.sql` | 管理员页验证多模型保存、选用与检测；对话链路验证主模型不可用时的自动切换 |