# 模块边界

## 前端边界
- `types/` 只定义消息、会话、图表和 KPI 类型，不依赖组件。
- `hooks/` 管理状态和副作用，例如 SSE 连接、输入状态和 loading 状态。
- `components/` 只负责展示和用户交互，不直接拼接后端 URL 或裸 `fetch()`。
- `App.tsx` 只做页面组合和顶层布局，不承载业务规则。

## 后端边界
- `main.py` 只负责 HTTP/SSE 协议层和路由注册。
- `config.py` 只负责环境变量读取和默认配置。
- `prompt_builder.py` 只负责读取 Skill 文档并构造 Prompt，不执行脚本。
- `runner.py` 负责 Agent 主循环、Skill 选择、脚本调度和消息整理。
- `renderers/` 负责把结构化结果转换为前端消息，不查询数据库。

## Skill 边界
- `SKILL.md` 描述触发条件、工作流、命令示例和安全边界。
- `scripts/` 放确定性执行入口，可以访问 MySQL，但不得依赖前端或 FastAPI 路由。
- 问数和决策建议 Skill 只执行 `SELECT`。
- 别名管理 Skill 只向 `alias_mapping` 插入已验证别名。

## 禁止跨界
- 前端组件禁止直接执行 SQL 或了解 Skill 脚本细节。
- Agent 禁止绕过 Skill 文档直接编造数据库操作。
- 渲染模块禁止修改数据库。
- LLM 禁止替代确定性脚本计算指标事实。
