-- 增量：应用用户、会话归属、用户记忆（从 001 升级时执行一次）
-- mysql -h127.0.0.1 -P3307 -udemo_user -pdemo_pass chatbi_demo < database/migrations/002_users_and_memory.sql
-- 若已执行过（重复列/约束），可按报错跳过对应语句。

USE chatbi_demo;

CREATE TABLE IF NOT EXISTS app_user (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(120) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(32) NOT NULL DEFAULT 'user',
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  UNIQUE KEY uq_app_user_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO app_user (username, password_hash, role, is_active)
VALUES (
  'admin',
  '$2b$12$iXi5Jzd4MR2HPoWaaai6pOmuDcivD9AF05G.knPmpp7Gp5drrSVYG',
  'admin',
  1
) ON DUPLICATE KEY UPDATE username = username;

ALTER TABLE chat_session ADD COLUMN user_id BIGINT NULL AFTER title;

UPDATE chat_session s
SET user_id = (SELECT id FROM app_user WHERE username = 'admin' LIMIT 1)
WHERE s.user_id IS NULL;

ALTER TABLE chat_session MODIFY COLUMN user_id BIGINT NOT NULL;

ALTER TABLE chat_session
  ADD CONSTRAINT fk_chat_session_user FOREIGN KEY (user_id) REFERENCES app_user (id);

ALTER TABLE chat_session
  ADD KEY idx_chat_session_user_updated (user_id, updated_at);

CREATE TABLE IF NOT EXISTS user_memory (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  kind VARCHAR(32) NOT NULL,
  title VARCHAR(512) NULL,
  content LONGTEXT NOT NULL,
  source_session_id BIGINT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  CONSTRAINT fk_user_memory_user FOREIGN KEY (user_id) REFERENCES app_user (id) ON DELETE CASCADE,
  CONSTRAINT fk_user_memory_session FOREIGN KEY (source_session_id) REFERENCES chat_session (id) ON DELETE SET NULL,
  KEY idx_user_memory_user_kind (user_id, kind, updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
