# 当前迭代

> 这是 Agent 的当前事实源，不保存完整流水账；历史细节看 Git 记录。

## 当前目标

保持 ChatBI Demo 可本地启动、可测试、可用中文完成问数 / 文件分析 / 管理配置 / 多 Agent 协作，并持续降低新 Agent 与同事接手成本。

## 快速状态

| 模块                        | 状态        | 备注                                                                                                  |
| --------------------------- | ----------- | ----------------------------------------------------------------------------------------------------- |
| 演示库与语义层              | ✅ 完成     | `chatbi_demo` + 语义元数据；Docker MySQL 默认 3307                                                    |
| Skill 体系                  | ✅ 完成     | semantic-query、alias-manager、decision-advisor、file-ingestion、chart/dashboard/database overview 等 |
| Agent / SSE                 | ✅ 完成     | Legacy + ReAct；支持 chart/kpi/text/error/done SSE                                                    |
| 前端对话 / 图表 / KPI       | ✅ 完成     | React 19 + ECharts 6                                                                                  |
| 会话 / 鉴权 / 记忆 / 管理页 | ✅ 完成     | 用户、数据源、LLM、多 Agents 管理                                                                     |
| 上传                        | ✅ 完成     | 文件分析                                                                                              |
| 自动化测试 / CI             | ✅ 完成     | `scripts/run_tests.py` 分套件；GitHub Actions 已配置                                                  |
| 端到端在线验收              | 🔄 按需执行 | 依赖本地数据库、后端和 LLM 可用                                                                       |

## 日常命令

| 场景          | 命令                                                                         |
| ------------- | ---------------------------------------------------------------------------- |
| 日常进场      | `bash scripts/bootstrap_dev.sh`                                              |
| 首次/依赖变动 | `bash scripts/bootstrap_dev.sh --sync`                                       |
| 代码清理      | `bash scripts/bootstrap_dev.sh --format`                                     |
| 快速测试      | `PYTHONPATH=. .venv/bin/python scripts/run_tests.py foundation -- -q`        |
| 开发启动      | `docker compose --env-file .env.dev -f docker-compose.dev.yml up -d --build` |
| 常规启动      | `docker compose up -d --build`                                               |

## 当前约定

- `.venv` 由 `uv sync` 按 `pyproject.toml` + `uv.lock` 管理；`requires-python = ">=3.11"`。
- 新增 Python 依赖只改 `pyproject.toml`，再执行 `uv lock`；Docker/CI 同样使用 `uv sync --frozen`。
- `bootstrap_dev.sh` 默认只配 Git hooks 和检查状态；不会自动跑 formatter。
- 代码改动后显式跑 `scripts/format_code.py` 或 `bootstrap_dev.sh --format`，再跑相关测试套件。
- 仅文档/说明改动不跑测试，只做必要自查。
- 新增 `tests/test_*.py` 必须先注册到 `scripts/run_tests.py` 的 `MODULE_SUITES`。

## 维护规则

- `活跃 Gap` 只保留未解决且会影响下一步执行的问题。
- `最近变更` 只保留最近 5 条；新增一条时删除最旧一条。
- 长期规则沉淀到 `AGENTS.md`、`README.md` 或对应专题文档，不放在本文件流水账里。

## 活跃 Gap

| 编号 | Gap                                                                               | 下一步                                                                                             |
| ---- | --------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| G1   | 从旧双 MySQL / 双 schema 拓扑切回单 schema 时，旧 `database/mysql-data-log/` 和旧日志库不会自动迁移 | 如需保留旧日志，先导出旧 `chatbi_local_logs.log` 后导入 `chatbi_demo`；纯净演示可 `down -v` 后重建 |
| G3   | 在线 E2E 不进默认 CI，依赖 LLM / DB / 后端运行状态                                | 后端和 LLM 可用时跑 `python scripts/e2e_smoke.py --cases S1,S4,E1` 或按需全量                      |
| G4   | 上传文件复杂跨字段分析 / 风控建议仍偏轻量规则                                     | 如要增强，新增上传数据分析或风控建议 Skill，不复用演示库 decision-advisor                          |
| G5   | `docs/architecture/README.md` 等专题文档可能仍滞后于 guide / backend-architecture | 改动相关模块时顺手同步；主用户/技术文档在 `docs/guide/`，后端专题见 `docs/backend-architecture.md` |

## 最近变更

| 轮次 | 完成内容                                                                                                                                                 | 验证                                                                                                                                                                                      |
| ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 244  | LLM 配置表单拆清“模型名”和“备注名”：模型名作为常驻输入项，选择厂商自动填推荐模型名，备注名留空时按模型名保存 | `.venv/bin/python scripts/format_code.py frontend/src/pages/LlmConfigPage.tsx`；`npm run build`；`git diff --check` |
| 243  | LLM 编辑已保存模型时 API Key 输入框改为禁用密文展示，保存编辑沿用原 profile 的 API Key 做未落库 probe 和更新，不再要求重新输入 Key | `.venv/bin/python scripts/format_code.py backend/routes/admin_llm_profiles_route.py frontend/src/api/client.ts frontend/src/pages/LlmConfigPage.tsx tests/test_admin_llm_profiles_probe.py`；`PYTHONPATH=. .venv/bin/python scripts/run_tests.py admin -- -q tests/test_admin_llm_profiles_probe.py`；`npm run build`；`git diff --check` |
| 242  | LLM 已保存模型去掉重复的“可用”状态标签；新增编辑按钮，可将已保存模型载入下方表单，重新填写 API Key 后仍按“先测试通过、再保存/启用”流程更新配置，并支持取消编辑 | `.venv/bin/python scripts/format_code.py frontend/src/pages/LlmConfigPage.tsx`；`npm run build`；`git diff --check` |
| 241  | LLM 新配置改为“先测试、后保存”：新增未落库 probe 接口，前端 `测试并启用` 只有连接测试通过才创建/更新已保存模型并启用，测试失败不会进入已保存列表 | `.venv/bin/python scripts/format_code.py backend/routes/admin_llm_profiles_route.py frontend/src/api/client.ts frontend/src/pages/LlmConfigPage.tsx scripts/run_tests.py tests/test_admin_llm_profiles_probe.py`；`PYTHONPATH=. .venv/bin/python scripts/run_tests.py admin -- -q tests/test_admin_llm_profiles_probe.py`；`npm run build`；`git diff --check` |
| 240  | LLM 配置页支持点击“已保存模型”卡片/选项卡直接切换当前模型；测试与删除按钮保持独立点击，不会误触发切换，并增加切换中状态反馈 | `.venv/bin/python scripts/format_code.py frontend/src/pages/LlmConfigPage.tsx`；`npm run build`；`git diff --check` |
