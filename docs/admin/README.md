# ChatBI 管理员手册

本文面向负责账号、模型、数据源、Skill、多 Agent 和部署运维的系统管理员。普通业务用户不需要阅读本文。

## 1. 管理员职责

管理员主要负责：

- 分配和维护用户账号。
- 配置可用的大模型服务。
- 维护业务数据源连接。
- 控制 Skill 和多 Agent 专线启用状态。
- 处理部署、健康检查、日志排查和安全配置。
- 在演示前确认默认账号、密钥和数据范围符合要求。

## 2. 登录与权限

系统支持普通用户和 `admin` 角色。管理员登录后可看到以下管理入口：

| 菜单 | 路径 | 用途 |
|---|---|---|
| 多 Agents 管理 | `/multi-agents` | 配置专线、每轮任务数和 Manager 轮数 |
| 技能管理 | `/skills` | 启用或禁用 Skill |
| 数据源管理 | `/data-sources` | 保存和测试 MySQL 连接 |
| LLM 配置 | `/llm` | 管理模型 Profile、测试连接并激活默认模型 |
| 用户管理 | `/users` | 创建账号、调整角色、重置密码、启停账号 |

生产或对外演示环境应开启鉴权，并设置强随机 `CHATBI_JWT_SECRET`。

## 3. 初始账号与鉴权

后端启动时会按环境变量中的 `CHATBI_SEED_USERS` 幂等写入种子用户：

```dotenv
CHATBI_SEED_USERS=admin:强密码:admin
```

建议：

- 首次部署后立即修改默认密码。
- 至少保留一个可用的管理员账号。
- 不要把生产密码提交到 Git。
- 对外演示前确认普通用户无法看到管理菜单。

开发脚本可能关闭登录，用于本地调试。生产式启动应保持前后端鉴权开关一致。

## 4. LLM 配置

在 `/llm` 中维护模型 Profile：

- 创建或编辑模型名、Base URL、API Key 和备注。
- 保存前先测试连接。
- 激活一条 Profile 作为运行时默认模型。
- 编辑已保存 Profile 时，API Key 会脱敏展示；如需更换 Key，需要重新填写并测试。

排查建议：

- 回答失败或长时间无响应时，先检查当前激活 Profile 是否可用。
- 如果服务商要求模型名前缀，按实际 LiteLLM 兼容格式填写。
- 不要把 API Key 暴露给普通用户或写入普通用户文档。

## 5. 数据源管理

在 `/data-sources` 中维护 MySQL 连接。对话页的“数据源连接 ID”可指定某条数据源记录。

建议：

- 优先接入只读账号。
- 演示环境不要直连未脱敏生产库。
- 保存前使用“测试连接”确认可达。
- 变更数据源后，用普通用户账号验证典型问法。

问数类 Skill 设计上只执行 `SELECT`，但数据源权限仍应在数据库层最小化。

## 6. Skill 管理

在 `/skills` 中控制 Skill 启用状态。禁用后，该 Skill 不会进入 Agent 可用能力列表。

常见 Skill：

| Skill | 用途 |
|---|---|
| `chatbi-semantic-query` | 语义层约束问数、排行、趋势 |
| `chatbi-comparison` | 环比和跨期对比 |
| `chatbi-decision-advisor` | 经营建议 |
| `chatbi-alias-manager` | 语义别名维护 |
| `chatbi-file-ingestion` | 上传文件解析 |
| `chatbi-auto-analysis` | 上传表指标提案与采纳看板 |
| `chatbi-chart-recommendation` | 图表推荐 |
| `chatbi-dashboard-orchestration` | 看板编排 |

变更 Skill 后建议做一次典型问法验证。

## 7. 多 Agent 管理

在 `/multi-agents` 中配置专线 registry。默认专线包括：

| 专线 | 职责 |
|---|---|
| A 线 `upload_analyst` | 上传文件解析与自动分析 |
| B 线 `demo_query` | 演示库问数、概览、指标解释 |
| C 线 `period_compare` | 环比和跨期对比 |
| D 线 `viz_board` | 图表和看板编排 |
| E 线 `semantic_config` | 语义别名维护 |
| F 线 `business_advisor` | 经营建议 |

关键参数：

- `max_agents_per_round`：每轮最多下发的子任务数。
- `max_manager_rounds`：Manager 最多调度轮数，管理页支持 1-8。

保存时系统会校验专线 id 与 Skill slug。registry 中引用的 Skill 应保持已注册且未禁用。

## 8. 部署与运行

生产式部署优先使用仓库根目录的 Docker 启动方式：

```bash
cp .env.example .env
bash scripts/launch.sh --no-open
```

必要配置包括：

```dotenv
OPENAI_API_KEY=你的模型Key
LLM_MODEL=openai/你的模型名
API_BASE=https://你的模型服务地址
CHATBI_JWT_SECRET=请替换为强随机密钥
CHATBI_SEED_USERS=admin:强密码:admin
```

常用运维命令：

```bash
docker compose ps
docker compose logs -f
docker compose down
bash scripts/launch.sh --no-build --no-open
```

默认访问：

- 应用：`http://服务器地址:5173`
- MySQL：`服务器地址:3307`

更完整的 CD 配置见 [CI/CD 文档](../ci-cd/README.md)。

## 9. 安全检查清单

上线或对外演示前检查：

- 已替换默认管理员密码。
- 已设置强随机 `CHATBI_JWT_SECRET`。
- API Key、数据库密码和 GitHub Secrets 未进入普通用户文档或截图。
- 普通用户账号看不到 `/llm`、`/users`、`/skills`、`/data-sources`、`/multi-agents`。
- 数据源使用最小权限账号，敏感数据已脱敏或隔离。
- 上传文件来源可信，且不包含未授权敏感信息。
- PDF 中文字体在目标环境可正常显示。

## 10. 故障排查

| 现象 | 优先检查 |
|---|---|
| 登录失败 | 用户状态、角色、密码、鉴权开关 |
| 普通用户看见管理菜单 | 前后端鉴权配置和用户角色 |
| 模型无响应 | LLM Profile、API Key、Base URL、服务商额度 |
| 问数失败 | 数据源连接、Skill 是否启用、语义层指标/维度 |
| 上传分析失败 | 文件格式、表头、上传 Skill 是否启用 |
| PDF 乱码 | 中文字体和部署镜像 |
| 生产健康检查失败 | `docker compose ps`、应用日志、`.env` 必要变量 |
