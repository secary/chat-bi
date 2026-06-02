# ChatBI 使用指南

本文面向需要**理解系统能力**并在浏览器中**实际操作**本项目的用户，侧重功能与页面说明，少量涉及部署与概念。实现细节见 [tech-guide.md](tech-guide.md)。

---

## 1. 这份文档适合谁

| 读者 | 能从本文得到什么 |
| -------- | -------------------------------------------------------------------- |
| 业务或产品试用者 | 每个菜单做什么、典型问题怎么问、结果怎么看 |
| 实施或运维人员 | 前后端如何启动、登录与权限、环境与端口大致关系 |
| 二次开发者 | 结合 [docs/architecture/README.md](../architecture/README.md) 理解分层与模块边界 |

更细的架构与 Agent 契约见 [docs/architecture/README.md](../architecture/README.md) 与设计文档 [docs/design/](../design/)。

---

## 2. 产品是什么、能做什么

**零眸智能 ChatBI** 是一个面向银行业务场景的**对话式数据分析 Demo**。用户用**中文自然语言**提问，系统在后台通过 **Agent + 技能（Skill）** 调用确定性脚本访问 **MySQL** 中的演示业务数据与语义层元数据，再通过网页以**文字、思考步骤、图表、KPI 卡片**等形式返回结果。

典型能力包括：

- **问数**：按指标、维度、时间范围查询销售额、订单、客户等（受语义层约束的只读查询）。
- **环比 / 对比**：按区域、渠道等维度做月度对比；支持「环比」「相对」「相较于」等自然说法。
- **经营决策建议**：在计算事实指标后，按规则生成可读的建议文本（常以 Markdown 展示）。
- **语义别名维护**：为指标或维度登记「别名 → 标准名」映射。
- **文件上传**：上传 CSV/XLSX 做结构校验、预览与后续分析。
- **上传表智能分析**：`chatbi-file-ingestion` 读取文件后，可由 `chatbi-auto-analysis` 生成**指标提案**；用户回复「采纳」后执行计算并展示**采纳看板**（图表 + KPI + 表格）。
- **多专线协作**：可选开启多 Agent 专线顺序执行并汇总（管理员在 registry 中配置六条专线）。
- **会话与记忆**：多轮对话按用户隔离；系统可注入长期偏好与近期摘要（可用 `CHATBI_MEMORY_DISABLED` 关闭）。
- **PDF 报告**：将当前会话导出为服务端生成的 PDF。

本项目定位为 **MVP / Demo**，权限模型为演示级。详细约束见 [README.md](../../README.md) 与各环境变量说明。

---

## 3. 技术栈与运行方式（概要）

| 层级 | 说明 |
| ---- | --------------------------------------------- |
| 前端 | React 19 + TypeScript + Vite + Tailwind CSS + ECharts 6 |
| 后端 | FastAPI，对话接口使用 **SSE** 流式返回思考与结果 |
| 模型调用 | LiteLLM；管理页可配置多条 **LLM Profile** 并激活其一 |
| 数据 | MySQL 8.0：`chatbi_demo`（业务 + 应用 + 管理 + 链路日志） |

**启动方式**请优先参考 [README.md](../../README.md)：

- **Docker 全栈（生产式本地）**：`chatbi-app` 暴露应用端口 **5173**；MySQL 宿主机 **3307**。
- **Docker 开发热更新**：`chatbi-app-dev` 同时承载 Vite 与 FastAPI reload；前端 **5174**，后端调试端口 **8001**，MySQL 宿主机 **33067**。`docker-compose.dev.yml` 中 `chatbi-db-dev` 使用 Docker named volume 保存 `chatbi_demo`。
- **宿主机开发**：本地运行后端与前端，MySQL 仍建议用 Docker。

宿主机 `.env` / `.env.dev` 默认只需要配置 `CHATBI_DB_*`；日志表默认写入同一个 `CHATBI_DB_NAME`。

环境变量模板见 `.env.example`；本地开发常配合 `.env.dev`（Git 忽略），约定见 [AGENTS.md](../../AGENTS.md)。

---

## 4. 登录、角色与鉴权开关

- **种子用户**：后端启动时按 `.env` / `.env.dev` 中的 `CHATBI_SEED_USERS=username:password:role;...` 幂等写入多个 `app_user`，其中管理员写成 `admin:密码:admin`。对外演示前**务必改密**。
- **角色**：普通用户与 **admin**。侧栏中「多 Agents 管理、技能管理、数据源、LLM、用户管理」仅 **admin** 可见。
- **开发 compose 默认关登录**：`docker-compose.dev.yml` 设置 `CHATBI_AUTH_ENABLED=false`，界面可能提示「开发环境：用户登录已关闭」，接口以种子用户身份运行。生产式 `docker-compose.yml` 应开启 JWT（`CHATBI_JWT_SECRET` 等，见 `.env.example`）。
- 前端是否展示登录页还受 `VITE_AUTH_ENABLED` 影响（与后端开关需一致）。

---

## 5. 界面总览：路由与侧栏

登录后（若开启鉴权），主布局为**左侧导航 + 右侧内容区**。

| 路由路径 | 菜单名称 | 谁能看见 | 主要内容 |
| --------------- | ----------- | ------ | --------------------------- |
| `/` | 对话 | 所有登录用户 | 问答、会话、上传、多专线、PDF、中止 |
| `/multi-agents` | 多 Agents 管理 | admin | registry、Manager 轮数、专线与技能 |
| `/skills` | 技能管理 | admin | Skill 启用/禁用 |
| `/data-sources` | 数据源管理 | admin | MySQL 连接、测试连接 |
| `/llm` | LLM 配置 | admin | 多 Profile、激活、测试连接 |
| `/users` | 用户管理 | admin | 账号与角色 |
| `/login` | （登录页） | 未登录 | 用户名密码登录 |

未匹配路径重定向到 `/`。

---

## 6. 各页面功能说明

### 6.1 对话页（`/`）

分为 **会话侧栏**、**顶部工具栏**、**消息与输入区**。

**会话侧栏**

- **会话列表**：标题随最近一次用户提问更新。
- **新对话** / **删除会话**：删除当前选中会话后会切换或新建。
- **收起 / 展开**：偏好保存在浏览器本地；上次选中会话 ID 会记住。

**顶部工具栏**

- **数据源连接 ID（可选）**：指定本轮使用的数据源记录 ID；留空则用默认连接。

**消息区**

助手消息可能包含：

- **思考步骤**：可折叠，展示 Agent 各步说明。
- **文本结论**：支持 **Markdown**（标题、列表、表格等）与 **KaTeX 公式**。
- **指标提案卡片**（`analysisProposal`）：上传表分析时展示建议指标列表、公式说明与置信度；用户可在对话中回复采纳。
- **采纳看板**（`dashboardReady`）：采纳指标后的 KPI 网格、图表与数据表；离开对话页再返回仍会恢复（已落库）。
- **图表** / **KPI 卡片** / **错误提示**：与问数、环比等 Skill 结果一致。

**生成中与离开页面**

- 助手生成时，输入区主按钮变为 **「中止」**：调用 `POST /abort` 并取消前端 SSE，停止后续 Skill。
- 若生成中离开页面再返回，可能显示 **「处理中」** 并轮询已落库的助手消息（`assistantPending`），避免空白。

**输入区**

- **文本输入**：支持短问法，如「1–4 月销售额排行」。
- **记忆 chip**：来自近期会话摘要的推荐追问，点击即发送。
- **附件**：CSV/XLSX 上传后会显示为待发送附件，随下一条用户问题进入分析链路。

**使用建议**

- 聊天页默认使用智能路由：简单问数通常走单 Agent，复合目标会自动切到多专线。
- 如果只说“给我建议”但没有指标、时间或区域范围，系统会先追问，而不是直接编造建议。
- 上传分析典型流程：上传文件 → 发送预填提示 → 查看指标提案 → 回复「采纳全部指标」或指定 ID → 查看采纳看板。

---

### 6.2 多 Agents 管理页（`/multi-agents`，仅 admin）

配置写入 `skills/_agents/registry.yaml` 的 **registry**，保存时服务端校验专线 id 与 Skill slug。

**全局参数**

- `max_agents_per_round`：每轮 Manager 下发的子任务条数上限（默认 4）。
- `max_manager_rounds`：协同调度最多轮数（管理页可配 1–8；仓库默认 5）。

**六条默认专线**（id → 职责摘要）

| 专线 id | 标签 | 主要 Skill |
|---------|------|------------|
| `upload_analyst` | A线 | `chatbi-file-ingestion`、`chatbi-auto-analysis` |
| `demo_query` | B线 | `chatbi-semantic-query`、`chatbi-database-overview`、`chatbi-semantic-processing`、`chatbi-metric-explainer` |
| `period_compare` | C线 | `chatbi-comparison` |
| `viz_board` | D线 | `chatbi-chart-recommendation`、`chatbi-dashboard-orchestration` |
| `semantic_config` | E线 | `chatbi-alias-manager` |
| `business_advisor` | F线 | `chatbi-decision-advisor` |

每条专线有独立的 `role_prompt`，限制模型不得越界调用其它专线 Skill。与「技能管理」配合：registry 中的 Skill 须已注册且未被禁用。

---

### 6.3 技能管理页（`/skills`，仅 admin）

查看并切换各 Skill 的启用状态（`admin_skill_registry`）。禁用后不会进入 Agent 的「可用 Skill」列表。

---

### 6.4 数据源管理页（`/data-sources`，仅 admin）

维护 MySQL 业务库连接并测试。对话页「数据源连接 ID」对应此处记录。

---

### 6.5 LLM 配置页（`/llm`，仅 admin）

- **多 Profile**：创建、编辑、删除、拖拽排序；**激活**一条作为运行时默认（可与环境变量合并，以后端解析为准）。
- **单条 / 批量测试连接**：验证 API Key 与 Base URL。
- 页面展示**当前生效**模型摘要，便于确认真实调用参数。

---

### 6.6 用户管理页（`/users`，仅 admin）

创建账号、分配角色（Demo 级）。

---

## 7. 典型使用场景

| 场景 | 你可以怎么说（示例） | 界面可能出现的内容 |
| ------- | ---------------------------------- | ----------------------------- |
| 排行 / 趋势 | 「2026 年 1–4 月各区域销售额排行」 | 表格 + 柱状图 + KPI |
| 环比对比 | 「各区域销售额环比」「4 月相较于 3 月毛利率」 | 对比表、分组柱图、环比 KPI |
| 决策建议 | 「基于当前数据给出经营决策建议」 | Markdown 建议 + 可能伴随 KPI |
| 别名维护 | 「把『营收』登记为销售额的别名」 | 写入确认类回复 |
| 复合意图 | 「查询华东销售额并给出建议」 | 多步思考或多段结果（可开多专线） |
| 上传 → 提案 → 看板 | 上传 CSV 后输入分析问题 →「采纳全部指标」 | 指标提案卡片 → Auto Analysis 看板 |

若结果不符预期，请检查：**LLM 是否可用**、**数据源 ID**、**相关 Skill 是否启用**、**多专线是否误开**。

---

## 8. 限制与已知约束（用户视角）

- **演示数据**：指标与维度以语义层与 `init.sql` 为准（默认 2026 年样例）。
- **安全边界**：问数类 Skill 仅 `SELECT`；别名写入受控表。勿将未评估的生产敏感数据接入 Demo 环境。
- **Skill 选用**：依赖 Prompt 中的选用时机/不要用说明与各专线边界，**无执行前硬校验**；错误选用需通过换问法或 Observation 纠正。
- **PDF 与中文**：缺中文字体时可能乱码，推荐在 Docker 镜像内导出。
- **文档漂移**：以 [README.md](../../README.md) 与 [current-sprint.md](../plans/current-sprint.md) 为准。

---

## 9. 相关文档索引

| 文档 | 内容 |
| --------------------------------------------------------- | ----------------------------- |
| [README.md](../../README.md) | 启动、端口、默认账号、目录结构 |
| [tech-guide.md](tech-guide.md) | Agent、Prompt、记忆、中止、Skill |
| [architecture/README.md](../architecture/README.md) | 分层与模块边界 |
| [plans/current-sprint.md](../plans/current-sprint.md) | 当前迭代与 Gap |

---

## 10. 文档修订说明

- 与仓库 `bf3/skillCall` 及后续 main 合并前功能对齐；重大变更请同步本节。
- 反馈请附带：浏览器路径、账号角色、是否关鉴权、响应头中的 `X-Trace-Id`。
