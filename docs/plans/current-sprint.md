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
