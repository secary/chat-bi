# 数据库增量迁移

若容器或本地 MySQL **已经初始化过旧版** `database/init.sql`（不含应用表），可在业务库上追加：

```bash
mysql -h127.0.0.1 -P3307 -udemo_user -pdemo_pass chatbi_demo < database/migrations/001_app_tables.sql
```

全新环境直接使用仓库中的完整 `database/init.sql` 初始化即可，无需单独执行本目录脚本。
