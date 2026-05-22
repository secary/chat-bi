# ChatBI Repository Instructions

在 GitHub Copilot cloud agent / online mode 中处理本仓库任务时，先快速读取：
- `AGENTS.md`
- `docs/plans/current-sprint.md`
- 与当前任务最相关的专题文档

遵守这些仓库事实：
- 后端：FastAPI + Python 3.11+ + LiteLLM
- 前端：React 19 + TypeScript + Vite + Tailwind CSS + ECharts 6
- 数据库：MySQL 8.0，Docker Compose，本地默认 3307
- 测试统一入口：`PYTHONPATH=. .venv/bin/python scripts/run_tests.py`

执行规则：
- 不回退或覆盖他人改动；默认工作区可能是脏的。
- 前端禁止 `console.log`，API 调用统一通过 `frontend/src/api/client.ts`。
- 新增测试文件必须注册到 `scripts/run_tests.py` 的 `MODULE_SUITES`。
- Python 相关命令优先使用 `.venv/bin/python`。
- 代码改动后先跑 `scripts/format_code.py`，再跑最小必要测试。
- 仅文档改动通常不跑测试，但需要做自查并同步 `docs/plans/current-sprint.md`。
- Skill 相关改动只触碰 `skills/<skill-name>/SKILL.md` 与其 `scripts/`；问数/决策脚本只执行 `SELECT`。

如果任务更偏专项，请优先选择仓库内自定义 agent：
- `.github/agents/testing-specialist.agent.md`
- `.github/agents/docs-specialist.agent.md`

如果没有使用专项 agent，也请遵守它们各自的职责边界：测试任务优先只改测试，文档任务优先只改文档。
