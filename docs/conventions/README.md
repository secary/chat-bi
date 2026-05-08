# 编码规范总览

## 文件组织
- 单文件 ≤ 300 行，超过则拆分
- 测试文件与源文件同目录，命名为 `*.test.ts` 或 `test_*.py`
- Skill 目录固定为 `skills/<skill-name>/SKILL.md` + 可选 `scripts/`

## 命名规范
- 组件：PascalCase
- 函数/变量：camelCase（TypeScript）或 snake_case（Python）
- 常量：UPPER_SNAKE_CASE
- 文件：kebab-case（前端）或 snake_case（Python 脚本）

## 错误处理
- 所有 async 函数必须有 try/catch
- 错误必须包含 code、message、context 三个字段
- 用户可见的错误信息必须友好，技术细节写入日志
- 脚本异常必须转换为前端 `error` 类型消息

## 日志规范
- 禁止 console.log
- 使用结构化日志：logger.info({ event, data, userId })
- 日志级别：error（需要立即处理）/ warn（需要关注）/ info（正常流程）

## 测试规范
- 新功能必须有单元测试
- 覆盖率目标 ≥ 80%
- 测试命名：describe('[模块名]') + it('should [行为]')
- Skill 脚本至少覆盖命令参数、成功输出、异常路径和安全边界
- Python 测试优先通过 `scripts/run_tests.py` 的模块套件执行，详见 `docs/testing/README.md`
- 新增 `tests/test_*.py` 必须加入 `scripts/run_tests.py` 的对应 `MODULE_SUITES`

## API 调用规范
- 统一通过 apiClient 封装，禁止裸 fetch()
- 所有请求必须处理 loading、success、error 三个状态
- SSE 消息必须符合 `thinking`、`text`、`chart`、`kpi_cards`、`error`、`done` 类型规范

## SQL 与语义层规范
- 问数和决策建议只允许执行 `SELECT`
- SQL 标识符和字面量必须使用安全转义
- 指标和维度必须优先来自 `metric_definition`、`dimension_definition` 和 `alias_mapping`
- 新别名必须映射到已有标准指标或维度，不得隐式创建新口径
