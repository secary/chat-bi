-- 增量：LLM 多档案（llm_model_profile）与 llm_settings.active_profile_id
-- mysql -h127.0.0.1 -P3307 -udemo_user -pdemo_pass chatbi_admin < database/migrations/004_llm_model_profiles.sql
-- 若已执行过（重复列/表），可按报错跳过对应语句。

USE chatbi_admin;

CREATE TABLE IF NOT EXISTS llm_model_profile (
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

ALTER TABLE llm_settings ADD COLUMN active_profile_id BIGINT NULL AFTER api_key;

INSERT INTO llm_model_profile (display_name, model, api_base, api_key, sort_order, health_status)
SELECT
  NULL,
  CASE
    WHEN NULLIF(TRIM(model), '') IS NOT NULL THEN TRIM(model)
    ELSE 'openai/gpt-4o-mini'
  END,
  NULLIF(TRIM(api_base), ''),
  NULLIF(TRIM(api_key), ''),
  0,
  'unknown'
FROM llm_settings
WHERE id = 1
  AND NOT EXISTS (SELECT 1 FROM llm_model_profile)
  AND (
    NULLIF(TRIM(model), '') IS NOT NULL
    OR NULLIF(TRIM(api_base), '') IS NOT NULL
    OR NULLIF(TRIM(api_key), '') IS NOT NULL
  );

UPDATE llm_settings s
SET
  active_profile_id = (SELECT MIN(p.id) FROM llm_model_profile p),
  model = NULL,
  api_base = NULL,
  api_key = NULL
WHERE s.id = 1
  AND s.active_profile_id IS NULL
  AND EXISTS (SELECT 1 FROM llm_model_profile);

ALTER TABLE llm_settings
  ADD CONSTRAINT fk_llm_settings_active_profile FOREIGN KEY (active_profile_id)
  REFERENCES llm_model_profile (id) ON DELETE SET NULL;
