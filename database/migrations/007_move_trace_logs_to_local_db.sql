-- 增量：将 trace 日志迁移到独立本地库 chatbi_local_logs
-- mysql -h127.0.0.1 -P33067 -uroot -proot123456 < database/migrations/007_move_trace_logs_to_local_db.sql

SET NAMES utf8mb4;

CREATE DATABASE IF NOT EXISTS chatbi_local_logs
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

GRANT ALL PRIVILEGES ON chatbi_local_logs.* TO 'demo_user'@'%';

CREATE TABLE IF NOT EXISTS chatbi_local_logs.chatbi_logs_trace_log (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  trace_id VARCHAR(64) NOT NULL,
  span_name VARCHAR(80) NOT NULL,
  event_name VARCHAR(80) NOT NULL,
  level VARCHAR(20) NOT NULL,
  message VARCHAR(500) NOT NULL,
  payload JSON NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  KEY idx_trace_log_trace_id (trace_id),
  KEY idx_trace_log_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET @sql = IF(
  EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'chatbi_demo' AND table_name = 'chatbi_logs_trace_log'
  ),
  'INSERT IGNORE INTO chatbi_local_logs.chatbi_logs_trace_log (id, trace_id, span_name, event_name, level, message, payload, created_at) SELECT id, trace_id, span_name, event_name, level, message, payload, created_at FROM chatbi_demo.chatbi_logs_trace_log',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = IF(
  EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'chatbi_logs' AND table_name = 'chatbi_trace_log'
  ),
  'INSERT IGNORE INTO chatbi_local_logs.chatbi_logs_trace_log (id, trace_id, span_name, event_name, level, message, payload, created_at) SELECT id, trace_id, span_name, event_name, level, message, payload, created_at FROM chatbi_logs.chatbi_trace_log',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
