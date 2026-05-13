-- 增量：将 app/admin/log 表收敛到 chatbi_demo，并使用原库名前缀命名
-- mysql -h127.0.0.1 -P3307 -udemo_user -pdemo_pass chatbi_demo < database/migrations/006_merge_feature_tables_with_prefixes.sql

SET NAMES utf8mb4;
USE chatbi_demo;

CREATE TABLE IF NOT EXISTS chatbi_app_user (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(120) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(32) NOT NULL DEFAULT 'user',
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  UNIQUE KEY uq_app_user_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS chatbi_app_chat_session (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(255) NOT NULL DEFAULT '新对话',
  user_id BIGINT NOT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  CONSTRAINT fk_chatbi_app_chat_session_user FOREIGN KEY (user_id) REFERENCES chatbi_app_user (id),
  KEY idx_chat_session_updated (updated_at),
  KEY idx_chat_session_user_updated (user_id, updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS chatbi_app_chat_message (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  session_id BIGINT NOT NULL,
  role VARCHAR(20) NOT NULL,
  content LONGTEXT NOT NULL,
  payload_json JSON NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  CONSTRAINT fk_chatbi_app_chat_message_session FOREIGN KEY (session_id)
    REFERENCES chatbi_app_chat_session(id) ON DELETE CASCADE,
  KEY idx_chat_message_session (session_id, id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS chatbi_app_user_memory (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  kind VARCHAR(32) NOT NULL,
  title VARCHAR(512) NULL,
  content LONGTEXT NOT NULL,
  source_session_id BIGINT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  CONSTRAINT fk_chatbi_app_user_memory_user FOREIGN KEY (user_id) REFERENCES chatbi_app_user (id) ON DELETE CASCADE,
  CONSTRAINT fk_chatbi_app_user_memory_session FOREIGN KEY (source_session_id)
    REFERENCES chatbi_app_chat_session (id) ON DELETE SET NULL,
  KEY idx_user_memory_user_kind (user_id, kind, updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS chatbi_admin_skill_registry (
  skill_slug VARCHAR(128) PRIMARY KEY,
  enabled TINYINT(1) NOT NULL DEFAULT 1,
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS chatbi_admin_app_db_connection (
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

CREATE TABLE IF NOT EXISTS chatbi_admin_llm_model_profile (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  display_name VARCHAR(128) NULL,
  model VARCHAR(255) NOT NULL,
  api_base VARCHAR(512) NULL,
  api_key VARCHAR(512) NULL,
  sort_order INT NOT NULL DEFAULT 0,
  supports_vision TINYINT(1) NOT NULL DEFAULT 0,
  health_status VARCHAR(16) NOT NULL DEFAULT 'unknown',
  health_detail VARCHAR(512) NULL,
  health_checked_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  KEY idx_llm_model_profile_sort (sort_order, id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS chatbi_admin_llm_settings (
  id INT PRIMARY KEY,
  model VARCHAR(255) NULL,
  api_base VARCHAR(512) NULL,
  api_key VARCHAR(512) NULL,
  active_profile_id BIGINT NULL,
  vision_profile_id BIGINT NULL,
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  CONSTRAINT fk_llm_settings_active_profile FOREIGN KEY (active_profile_id)
    REFERENCES chatbi_admin_llm_model_profile (id) ON DELETE SET NULL,
  CONSTRAINT fk_llm_settings_vision_profile FOREIGN KEY (vision_profile_id)
    REFERENCES chatbi_admin_llm_model_profile (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS chatbi_logs_trace_log (
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
  EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'chatbi_demo' AND table_name = 'app_user'),
  'INSERT IGNORE INTO chatbi_app_user (id, username, password_hash, role, is_active, created_at) SELECT id, username, password_hash, role, is_active, created_at FROM app_user',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = IF(
  EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'chatbi_app' AND table_name = 'app_user'),
  'INSERT IGNORE INTO chatbi_app_user (id, username, password_hash, role, is_active, created_at) SELECT id, username, password_hash, role, is_active, created_at FROM chatbi_app.app_user',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = IF(
  EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'chatbi_demo' AND table_name = 'chat_session'),
  'INSERT IGNORE INTO chatbi_app_chat_session (id, title, user_id, created_at, updated_at) SELECT id, title, user_id, created_at, updated_at FROM chat_session',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = IF(
  EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'chatbi_app' AND table_name = 'chat_session'),
  'INSERT IGNORE INTO chatbi_app_chat_session (id, title, user_id, created_at, updated_at) SELECT id, title, user_id, created_at, updated_at FROM chatbi_app.chat_session',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = IF(
  EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'chatbi_demo' AND table_name = 'chat_message'),
  'INSERT IGNORE INTO chatbi_app_chat_message (id, session_id, role, content, payload_json, created_at) SELECT id, session_id, role, content, payload_json, created_at FROM chat_message',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = IF(
  EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'chatbi_app' AND table_name = 'chat_message'),
  'INSERT IGNORE INTO chatbi_app_chat_message (id, session_id, role, content, payload_json, created_at) SELECT id, session_id, role, content, payload_json, created_at FROM chatbi_app.chat_message',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = IF(
  EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'chatbi_demo' AND table_name = 'user_memory'),
  'INSERT IGNORE INTO chatbi_app_user_memory (id, user_id, kind, title, content, source_session_id, created_at, updated_at) SELECT id, user_id, kind, title, content, source_session_id, created_at, updated_at FROM user_memory',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = IF(
  EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'chatbi_app' AND table_name = 'user_memory'),
  'INSERT IGNORE INTO chatbi_app_user_memory (id, user_id, kind, title, content, source_session_id, created_at, updated_at) SELECT id, user_id, kind, title, content, source_session_id, created_at, updated_at FROM chatbi_app.user_memory',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = IF(
  EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'chatbi_demo' AND table_name = 'skill_registry'),
  'INSERT INTO chatbi_admin_skill_registry (skill_slug, enabled, updated_at) SELECT skill_slug, enabled, updated_at FROM skill_registry ON DUPLICATE KEY UPDATE enabled = VALUES(enabled), updated_at = VALUES(updated_at)',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = IF(
  EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'chatbi_admin' AND table_name = 'skill_registry'),
  'INSERT INTO chatbi_admin_skill_registry (skill_slug, enabled, updated_at) SELECT skill_slug, enabled, updated_at FROM chatbi_admin.skill_registry ON DUPLICATE KEY UPDATE enabled = VALUES(enabled), updated_at = VALUES(updated_at)',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = IF(
  EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'chatbi_demo' AND table_name = 'app_db_connection'),
  'INSERT IGNORE INTO chatbi_admin_app_db_connection (id, name, host, port, username, password, database_name, is_default, created_at) SELECT id, name, host, port, username, password, database_name, is_default, created_at FROM app_db_connection',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = IF(
  EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'chatbi_admin' AND table_name = 'app_db_connection'),
  'INSERT IGNORE INTO chatbi_admin_app_db_connection (id, name, host, port, username, password, database_name, is_default, created_at) SELECT id, name, host, port, username, password, database_name, is_default, created_at FROM chatbi_admin.app_db_connection',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = IF(
  EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'chatbi_demo' AND table_name = 'llm_model_profile'),
  IF(
    EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'chatbi_demo' AND table_name = 'llm_model_profile' AND column_name = 'supports_vision'),
    'INSERT IGNORE INTO chatbi_admin_llm_model_profile (id, display_name, model, api_base, api_key, sort_order, supports_vision, health_status, health_detail, health_checked_at, created_at, updated_at) SELECT id, display_name, model, api_base, api_key, sort_order, COALESCE(supports_vision, 0), COALESCE(health_status, ''unknown''), health_detail, health_checked_at, created_at, updated_at FROM llm_model_profile',
    'INSERT IGNORE INTO chatbi_admin_llm_model_profile (id, display_name, model, api_base, api_key, sort_order, supports_vision, health_status, health_detail, health_checked_at, created_at, updated_at) SELECT id, display_name, model, api_base, api_key, sort_order, 0, ''unknown'', NULL, NULL, created_at, updated_at FROM llm_model_profile'
  ),
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = IF(
  EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'chatbi_admin' AND table_name = 'llm_model_profile'),
  IF(
    EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'chatbi_admin' AND table_name = 'llm_model_profile' AND column_name = 'supports_vision'),
    'INSERT IGNORE INTO chatbi_admin_llm_model_profile (id, display_name, model, api_base, api_key, sort_order, supports_vision, health_status, health_detail, health_checked_at, created_at, updated_at) SELECT id, display_name, model, api_base, api_key, sort_order, COALESCE(supports_vision, 0), COALESCE(health_status, ''unknown''), health_detail, health_checked_at, created_at, updated_at FROM chatbi_admin.llm_model_profile',
    'INSERT IGNORE INTO chatbi_admin_llm_model_profile (id, display_name, model, api_base, api_key, sort_order, supports_vision, health_status, health_detail, health_checked_at, created_at, updated_at) SELECT id, display_name, model, api_base, api_key, sort_order, 0, ''unknown'', NULL, NULL, created_at, updated_at FROM chatbi_admin.llm_model_profile'
  ),
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = IF(
  EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'chatbi_demo' AND table_name = 'llm_settings'),
  IF(
    EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'chatbi_demo' AND table_name = 'llm_settings' AND column_name = 'vision_profile_id'),
    'INSERT INTO chatbi_admin_llm_settings (id, model, api_base, api_key, active_profile_id, vision_profile_id, updated_at) SELECT id, model, api_base, api_key, active_profile_id, vision_profile_id, updated_at FROM llm_settings ON DUPLICATE KEY UPDATE model = VALUES(model), api_base = VALUES(api_base), api_key = VALUES(api_key), active_profile_id = VALUES(active_profile_id), vision_profile_id = VALUES(vision_profile_id), updated_at = VALUES(updated_at)',
    IF(
      EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'chatbi_demo' AND table_name = 'llm_settings' AND column_name = 'active_profile_id'),
      'INSERT INTO chatbi_admin_llm_settings (id, model, api_base, api_key, active_profile_id, vision_profile_id, updated_at) SELECT id, model, api_base, api_key, active_profile_id, NULL, updated_at FROM llm_settings ON DUPLICATE KEY UPDATE model = VALUES(model), api_base = VALUES(api_base), api_key = VALUES(api_key), active_profile_id = VALUES(active_profile_id), vision_profile_id = VALUES(vision_profile_id), updated_at = VALUES(updated_at)',
      'INSERT INTO chatbi_admin_llm_settings (id, model, api_base, api_key, active_profile_id, vision_profile_id, updated_at) SELECT id, model, api_base, api_key, NULL, NULL, updated_at FROM llm_settings ON DUPLICATE KEY UPDATE model = VALUES(model), api_base = VALUES(api_base), api_key = VALUES(api_key), active_profile_id = VALUES(active_profile_id), vision_profile_id = VALUES(vision_profile_id), updated_at = VALUES(updated_at)'
    )
  ),
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = IF(
  EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'chatbi_admin' AND table_name = 'llm_settings'),
  IF(
    EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'chatbi_admin' AND table_name = 'llm_settings' AND column_name = 'vision_profile_id'),
    'INSERT INTO chatbi_admin_llm_settings (id, model, api_base, api_key, active_profile_id, vision_profile_id, updated_at) SELECT id, model, api_base, api_key, active_profile_id, vision_profile_id, updated_at FROM chatbi_admin.llm_settings ON DUPLICATE KEY UPDATE model = VALUES(model), api_base = VALUES(api_base), api_key = VALUES(api_key), active_profile_id = VALUES(active_profile_id), vision_profile_id = VALUES(vision_profile_id), updated_at = VALUES(updated_at)',
    IF(
      EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'chatbi_admin' AND table_name = 'llm_settings' AND column_name = 'active_profile_id'),
      'INSERT INTO chatbi_admin_llm_settings (id, model, api_base, api_key, active_profile_id, vision_profile_id, updated_at) SELECT id, model, api_base, api_key, active_profile_id, NULL, updated_at FROM chatbi_admin.llm_settings ON DUPLICATE KEY UPDATE model = VALUES(model), api_base = VALUES(api_base), api_key = VALUES(api_key), active_profile_id = VALUES(active_profile_id), vision_profile_id = VALUES(vision_profile_id), updated_at = VALUES(updated_at)',
      'INSERT INTO chatbi_admin_llm_settings (id, model, api_base, api_key, active_profile_id, vision_profile_id, updated_at) SELECT id, model, api_base, api_key, NULL, NULL, updated_at FROM chatbi_admin.llm_settings ON DUPLICATE KEY UPDATE model = VALUES(model), api_base = VALUES(api_base), api_key = VALUES(api_key), active_profile_id = VALUES(active_profile_id), vision_profile_id = VALUES(vision_profile_id), updated_at = VALUES(updated_at)'
    )
  ),
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = IF(
  EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'chatbi_logs' AND table_name = 'chatbi_trace_log'),
  'INSERT IGNORE INTO chatbi_logs_trace_log (id, trace_id, span_name, event_name, level, message, payload, created_at) SELECT id, trace_id, span_name, event_name, level, message, payload, created_at FROM chatbi_logs.chatbi_trace_log',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = IF(
  EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'chatbi_demo' AND table_name = 'chatbi_trace_log'),
  'INSERT IGNORE INTO chatbi_logs_trace_log (id, trace_id, span_name, event_name, level, message, payload, created_at) SELECT id, trace_id, span_name, event_name, level, message, payload, created_at FROM chatbi_trace_log',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

INSERT INTO chatbi_app_user (username, password_hash, role, is_active)
VALUES (
  'admin',
  '$2b$12$iXi5Jzd4MR2HPoWaaai6pOmuDcivD9AF05G.knPmpp7Gp5drrSVYG',
  'admin',
  1
)
ON DUPLICATE KEY UPDATE id = id;

INSERT INTO chatbi_admin_llm_settings (id, model, api_base, api_key, active_profile_id, vision_profile_id)
VALUES (1, NULL, NULL, NULL, NULL, NULL)
ON DUPLICATE KEY UPDATE id = id;
