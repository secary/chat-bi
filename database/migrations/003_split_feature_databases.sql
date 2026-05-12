-- 将原先混放在 chatbi_demo 中的应用表按功能拆分到独立数据库
-- 示例：
-- mysql -h127.0.0.1 -P3308 -udemo_user -pdemo_pass < database/migrations/003_split_feature_databases.sql

SET NAMES utf8mb4;

CREATE DATABASE IF NOT EXISTS chatbi_app
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

CREATE DATABASE IF NOT EXISTS chatbi_admin
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS chatbi_app.app_user (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(120) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(32) NOT NULL DEFAULT 'user',
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  UNIQUE KEY uq_app_user_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS chatbi_app.chat_session (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(255) NOT NULL DEFAULT '新对话',
  user_id BIGINT NOT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  CONSTRAINT fk_chat_session_user FOREIGN KEY (user_id) REFERENCES chatbi_app.app_user (id),
  KEY idx_chat_session_updated (updated_at),
  KEY idx_chat_session_user_updated (user_id, updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS chatbi_app.chat_message (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  session_id BIGINT NOT NULL,
  role VARCHAR(20) NOT NULL,
  content LONGTEXT NOT NULL,
  payload_json JSON NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  CONSTRAINT fk_chat_message_session FOREIGN KEY (session_id)
    REFERENCES chatbi_app.chat_session(id) ON DELETE CASCADE,
  KEY idx_chat_message_session (session_id, id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS chatbi_app.user_memory (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  kind VARCHAR(32) NOT NULL,
  title VARCHAR(512) NULL,
  content LONGTEXT NOT NULL,
  source_session_id BIGINT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  CONSTRAINT fk_user_memory_user FOREIGN KEY (user_id) REFERENCES chatbi_app.app_user (id) ON DELETE CASCADE,
  CONSTRAINT fk_user_memory_session FOREIGN KEY (source_session_id) REFERENCES chatbi_app.chat_session (id) ON DELETE SET NULL,
  KEY idx_user_memory_user_kind (user_id, kind, updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS chatbi_admin.skill_registry (
  skill_slug VARCHAR(128) PRIMARY KEY,
  enabled TINYINT(1) NOT NULL DEFAULT 1,
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS chatbi_admin.app_db_connection (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(120) NOT NULL,
  host VARCHAR(255) NOT NULL,
  port INT NOT NULL DEFAULT 3306,
  username VARCHAR(120) NOT NULL,
  password VARCHAR(512) NOT NULL,
  database_name VARCHAR(120) NOT NULL,
  is_default TINYINT(1) NOT NULL DEFAULT 0,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  UNIQUE KEY uq_app_db_connection_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS chatbi_admin.llm_model_profile (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  display_name VARCHAR(128) NULL,
  model VARCHAR(255) NOT NULL,
  api_base VARCHAR(512) NULL,
  api_key VARCHAR(512) NULL,
  sort_order INT NOT NULL DEFAULT 0,
  health_status VARCHAR(16) NOT NULL DEFAULT 'unknown',
  health_detail VARCHAR(512) NULL,
  health_checked_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  KEY idx_llm_model_profile_sort (sort_order, id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS chatbi_admin.llm_settings (
  id INT PRIMARY KEY,
  model VARCHAR(255) NULL,
  api_base VARCHAR(512) NULL,
  api_key VARCHAR(512) NULL,
  active_profile_id BIGINT NULL,
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  CONSTRAINT fk_llm_settings_active_profile FOREIGN KEY (active_profile_id)
    REFERENCES chatbi_admin.llm_model_profile (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO chatbi_app.app_user
  (id, username, password_hash, role, is_active, created_at)
SELECT id, username, password_hash, role, is_active, created_at
FROM chatbi_demo.app_user;

INSERT IGNORE INTO chatbi_app.chat_session
  (id, title, user_id, created_at, updated_at)
SELECT id, title, user_id, created_at, updated_at
FROM chatbi_demo.chat_session;

INSERT IGNORE INTO chatbi_app.chat_message
  (id, session_id, role, content, payload_json, created_at)
SELECT id, session_id, role, content, payload_json, created_at
FROM chatbi_demo.chat_message;

INSERT IGNORE INTO chatbi_app.user_memory
  (id, user_id, kind, title, content, source_session_id, created_at, updated_at)
SELECT id, user_id, kind, title, content, source_session_id, created_at, updated_at
FROM chatbi_demo.user_memory;

INSERT INTO chatbi_admin.skill_registry (skill_slug, enabled, updated_at)
SELECT skill_slug, enabled, updated_at
FROM chatbi_demo.skill_registry
ON DUPLICATE KEY UPDATE
  enabled = VALUES(enabled),
  updated_at = VALUES(updated_at);

INSERT INTO chatbi_admin.app_db_connection
  (id, name, host, port, username, password, database_name, is_default, created_at)
SELECT id, name, host, port, username, password, database_name, is_default, created_at
FROM chatbi_demo.app_db_connection
ON DUPLICATE KEY UPDATE
  name = VALUES(name),
  host = VALUES(host),
  port = VALUES(port),
  username = VALUES(username),
  password = VALUES(password),
  database_name = VALUES(database_name),
  is_default = VALUES(is_default),
  created_at = VALUES(created_at);

INSERT INTO chatbi_admin.llm_model_profile
  (display_name, model, api_base, api_key, sort_order, health_status, created_at, updated_at)
SELECT
  NULL,
  CASE
    WHEN NULLIF(TRIM(ls.model), '') IS NOT NULL THEN TRIM(ls.model)
    ELSE 'openai/gpt-4o-mini'
  END,
  NULLIF(TRIM(ls.api_base), ''),
  NULLIF(TRIM(ls.api_key), ''),
  0,
  'unknown',
  ls.updated_at,
  ls.updated_at
FROM chatbi_demo.llm_settings ls
WHERE ls.id = 1
  AND (
    NULLIF(TRIM(ls.model), '') IS NOT NULL
    OR NULLIF(TRIM(ls.api_base), '') IS NOT NULL
    OR NULLIF(TRIM(ls.api_key), '') IS NOT NULL
  )
  AND NOT EXISTS (SELECT 1 FROM chatbi_admin.llm_model_profile);

INSERT INTO chatbi_admin.llm_settings
  (id, model, api_base, api_key, active_profile_id, updated_at)
SELECT
  ls.id,
  CASE WHEN EXISTS (SELECT 1 FROM chatbi_admin.llm_model_profile p) THEN NULL ELSE ls.model END,
  CASE WHEN EXISTS (SELECT 1 FROM chatbi_admin.llm_model_profile p) THEN NULL ELSE ls.api_base END,
  CASE WHEN EXISTS (SELECT 1 FROM chatbi_admin.llm_model_profile p) THEN NULL ELSE ls.api_key END,
  (SELECT MIN(p.id) FROM chatbi_admin.llm_model_profile p),
  ls.updated_at
FROM chatbi_demo.llm_settings ls
WHERE ls.id = 1
ON DUPLICATE KEY UPDATE
  model = VALUES(model),
  api_base = VALUES(api_base),
  api_key = VALUES(api_key),
  active_profile_id = VALUES(active_profile_id),
  updated_at = VALUES(updated_at);
