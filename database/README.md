# Database 目录说明

## 当前初始化入口

- `init.sql`
  - 主初始化脚本。
  - 创建并填充 `chatbi_demo`（业务 + 语义层 + 应用前缀表 + 管理前缀表）。
  - 默认管理员由后端启动时按 `CHATBI_DEFAULT_ADMIN_*` 环境变量幂等写入。
- `init_log.sql`
  - 独立日志库初始化脚本。
  - 仅创建 `chatbi_local_logs.chatbi_logs_trace_log`。

## 运行生成物

- `mysql-data/`
  - 历史单实例宿主机 MySQL 数据目录，可清理。
- `mysql-data-dev/`
  - 历史开发态宿主机 MySQL 数据目录；当前 `docker-compose.dev.yml` 已改用 named volume，不再作为主开发库默认挂载。
- `mysql-data-log/`
  - 当前独立日志实例 `log-mysql` 的宿主机数据目录。

## 清理建议

- 可以直接删除：
  - 误生成的空目录、`.DS_Store` 这类宿主机垃圾文件。
  - 不再使用的旧 `mysql-data/`、`mysql-data-dev/` 数据目录，但删除前先确认你不需要保留旧演示数据。
- 不建议直接手删：
  - 正在被 MySQL 容器使用的真实数据目录内容。
