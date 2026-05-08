# 自动化测试框架

ChatBI 的测试先按功能模块组织执行入口，暂时保留 `tests/` 扁平文件结构，避免一次性搬迁造成大量路径 churn。

## 提交前本地检查

```bash
# 代码格式与 lint
.venv/bin/ruff check backend/ scripts/ tests/
.venv/bin/black --check backend/ scripts/ tests/

# 后端测试（快速套件）
PYTHONPATH=. .venv/bin/python scripts/run_tests.py quick -- -q

# 前端
cd frontend && npm run lint && npm run test && npm run build
```

## 统一入口

```bash
PYTHONPATH=. .venv/bin/python scripts/run_tests.py --list
PYTHONPATH=. .venv/bin/python scripts/run_tests.py quick -- -q
PYTHONPATH=. .venv/bin/python scripts/run_tests.py agent admin -- -q
PYTHONPATH=. .venv/bin/python scripts/run_tests.py all --frontend
```

依赖查看或安装使用 uv 管理的项目解释器：

```bash
uv pip --python .venv/bin/python show pytest pymysql
uv pip --python .venv/bin/python install -r requirements.txt
```

## 模块套件

| 套件 | 覆盖范围 |
|------|----------|
| `foundation` | 环境加载、HTTP 工具、协议、Observation、测试框架自检 |
| `skills` | Skill 确定性脚本、输出契约、安全边界 |
| `agent` | Legacy/ReAct runner、多专线、上下文、断连与复合意图 |
| `admin` | 管理接口、技能注册、多 Agent 配置、数据库目标 |
| `auth-memory` | 鉴权、token、免登录、记忆开关 |
| `dashboard` | Dashboard 聚合和图表渲染 |
| `data-sources` | 外部库 SQL、数据库概览、文件导入 |
| `upload-vision` | 上传上下文、文件解析、视觉抽取 |
| `report` | PDF 报告 |

便捷别名：

| 别名 | 等价套件 |
|------|----------|
| `quick` | `foundation + skills + data-sources` |
| `backend` | `admin + dashboard + report` |
| `auth` | `auth-memory` |
| `data` | `data-sources` |

## 新增测试规则

1. 新功能必须先判断归属模块，并把测试文件加入 `scripts/run_tests.py` 的对应 `MODULE_SUITES`。
2. 如果新增了 `tests/test_*.py` 却没有归属套件，`tests/test_run_tests_script.py` 会失败。
3. 日常提交前优先跑 `quick`；改 Agent 跑 `agent`；改管理/仪表盘/PDF 跑对应模块。
4. 需要全量 Python 测试时跑 `all`；需要前端 Vitest 时加 `--frontend`。
5. 前端测试仍使用 `cd frontend && npm run test`，由 `scripts/run_tests.py --frontend` 统一串联。

## 具体用例索引

当前 Python 全量收集为 83 个用例。下面按功能域列出核心保护点，精确用例名可用 `PYTHONPATH=. .venv/bin/python -m pytest --collect-only -q tests` 查看。

### Foundation

- `test_env_loader.py::EnvLoaderTest::test_dev_env_overrides_base_env`：`.env.dev` 覆盖基础 `.env`。
- `test_http_utils.py::test_request_trace_id_uses_header_when_valid`：合法 `X-Trace-Id` 透传。
- `test_http_utils.py::test_request_trace_id_generates_when_header_invalid`：非法 trace id 自动生成。
- `test_observation.py::ObservationTest::test_summarize_table_includes_row_count_and_samples`：Observation 摘要包含行数、列和样例。
- `test_skill_result_log_payload.py::SkillResultLogPayloadTest::test_extracts_query_intent_summary`：Skill 日志提取 query intent 摘要。
- `test_agent_skill_protocol.py::SkillProtocolTest::test_normalizes_legacy_table_rows`：旧表格行归一化为 SkillResult。
- `test_agent_skill_protocol.py::SkillProtocolTest::test_prefers_skill_chart_plan_over_llm_plan`：Skill 返回图表计划优先于 LLM 计划。
- `test_agent_skill_protocol.py::SkillProtocolTest::test_streams_structured_decision_result`：决策结果输出 text 与 KPI。
- `test_run_tests_script.py::*`：模块套件路径存在、全量发现、归属覆盖、重复去重。

### Skills

- `test_chart_recommendation_skill.py::*`：图表推荐在缺数据时澄清，支持自然语言 + JSON 输入，排行行输出图表，单指标输出 KPI。
- `test_dashboard_orchestration_skill.py::*`：Dashboard overview 转看板规格，支持混合输入，缺源数据时澄清。
- `test_database_overview_skill.py::*`：数据库概览区分业务资产和语义层资产，并补充字段/指标说明。
- `test_decision_advisor_focus.py::*`：决策建议能解析指标/维度焦点，并按毛利率、区域过滤建议。
- `test_file_ingestion_skill.py::*`：读取销售订单 CSV 中文表头和客户画像 XLSX。
- `test_metric_explainer_skill.py::*`：通过别名解释指标，提取公式字段并渲染字段说明。
- `test_semantic_processing_skill.py::*`：语义处理覆盖 ready、need clarification、趋势补时间维度。

### Agent

- `test_agent_runner_contract.py::*`：Legacy 模式一次计划一次脚本，小聊天跳过 planner 和 skill。
- `test_agent_workflow.py::*`：复合“查询 + 建议”拆成 semantic-query → decision-advisor；普通查询保持单步；prompt 包含数据库概览触发规则。
- `test_chat_route_disconnect.py::*`：前端断连状态一旦出现保持生效。
- `test_multi_agent_registry.py::*`：按 slug 顺序过滤已启用 Skill。
- `test_multi_agent_router.py::*`：路由 LLM JSON 调用和专线数量上限。
- `test_query_advice_dimension_flow.py::*`：从查询结果首列推断建议关注维度。
- `test_react_runner.py::*`：ReAct 两轮调用、无 skill finish、寒暄短路、可视化优先 Skill 保图表。
- `test_upload_context.py::*`：历史上传文件路径注入上下文，纯数据库问题不注入。

### Admin / Auth / Memory

- `test_admin_multi_agents.py::*`：多 Agent 管理默认值、保存回读、非法 Skill/agent/空配置拒绝、registry 原子写。
- `test_db_mysql_targets.py::*`：app/admin 目标库配置路由正确。
- `test_skill_registry_graceful.py::*`：`skill_registry` 查询失败时降级为空禁用集。
- `test_auth_deps_disabled.py::*`：免登录 dev user、非 admin dev id 回退种子 admin、开启鉴权时必须凭据。
- `test_auth_password.py::*`：密码 hash roundtrip。
- `test_auth_tokens.py::*`：JWT roundtrip。
- `test_memory_service_off.py::*`：记忆关闭时格式化为空。

### Dashboard / Data Sources

- `test_dashboard_overview.py::*`：Dashboard overview 返回 KPI/图表/语义计数结构，非法表名 count 安全。
- `test_chart_renderer.py::*`：图表渲染器缺 plan 字段时自动推断，空 rows 保持空 option。
- `test_external_bank_demo_sql.py::*`：外部银行库 SQL 创建独立库、覆盖银行关联表、保留 ChatBI 兼容面和银行语义别名。

### Upload / Vision / Report

- `test_vision_extract.py::*`：Vision 抽取空结果归一化、行数截断。
- `test_report_pdf.py::*`：PDF HTML 文档、chart base64、WeasyPrint 成功路径、ReportLab fallback、CJK 字体优先、LLM 摘要 mock。

## 迁移方向

当前阶段只统一执行入口和模块归属。后续如果要瘦身 `tests/` 根目录，可按同名模块逐步迁移到：

```text
tests/foundation/
tests/skills/
tests/agent/
tests/admin/
tests/auth_memory/
tests/dashboard/
tests/data_sources/
tests/upload_vision/
tests/report/
```

迁移时保持 `scripts/run_tests.py` 作为唯一入口，避免不同 Agent 各自发明测试命令。
