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
| 29 | 支持复合问题工作流：当用户一句话同时要求“先排行/查询，再给经营建议/意见”时，Agent 在单轮中先执行 `chatbi-semantic-query`，再执行 `chatbi-decision-advisor`；前端同一条消息支持自然拼接两段文本；补工作流单测 | 首版双步骤曾依赖 planner 先选中 `chatbi-semantic-query`，且“决策意见/经营意见”这类措辞未被纳入复合意图识别；现已改为按用户原句识别“查询 + 建议/意见”并强制双步骤，但尚未泛化为任意多 Skill 工作流 | 在 Docker 环境重建 backend/frontend 后，验证 `1-4月销售额排行并给出经营决策建议`、`1-4月销售额排行及决策意见` 的端到端展示效果，并观察是否需要把查询结果与建议分栏展示 |
| 30 | 新增 `chatbi-metric-explainer` Skill：支持按指标名或指标别名解释业务口径、计算公式、来源表、常用维度和相关字段；补本地单测 | 当前只覆盖指标解释，不覆盖维度解释、业务术语解释或多指标对比解释；默认返回文本，不生成图表 | 将新 Skill 接入端到端联调，验证 `销售额口径是什么`、`解释一下毛利率`、`收入这个指标是什么意思` 的实际回答效果 |
| 31 | 优化 `query -> advice` 复合链路：将查询结果首列维度透传给 `chatbi-decision-advisor`，并在决策脚本中按关注维度裁剪建议主题；新增维度聚焦单测 | 当前只实现了“主维度驱动建议文本”的第一步，尚未把决策图表/KPI 也同步收敛到同一维度，也未覆盖更复杂的双维分析场景 | 端到端验证 `1-4月销售额排行并给出决策意见` 时建议是否明显围绕区域展开；后续再补维度化图表/KPI 输出 |
| 32 | 增加确定性技能路由兜底：对高置信度问数、指标解释、别名维护和纯建议问句在 runner 层强制纠偏 skill；当问数被纠偏为 `chatbi-semantic-query` 时自动补基础 chart plan；补路由单测 | 当前仍以关键词/规则为主，复杂歧义句和多意图句仍可能需要更细的语义路由；基础 chart plan 只覆盖常见柱状/折线/饼图启发式 | 在端到端验证 `按照产品划分销售额`、`销售额口径是什么`、`给我经营建议` 的实际技能选择是否稳定 |
