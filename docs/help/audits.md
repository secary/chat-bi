# 审计说明

面向管理员，说明如何通过 trace 查看对话和 Agent 执行链路。

## 什么时候看审计

- 回答结果不符合预期。
- Skill 选择异常或多 Agent 路由异常。
- LLM 配置测试、保存或启用异常。
- 需要排查某轮对话的请求、Observation 和错误信息。

## 排查线索

- 优先使用对话页展示的当前 trace 或最近 trace。
- 关注 execution_decision、route_transition、skill_result 和 fallback 事件。
- LLM 配置链路关注 profile_probe_tested、profile_tested 和 active_profile_set 事件。
- 不要把包含密钥或敏感数据的 trace 截图发给普通用户。
