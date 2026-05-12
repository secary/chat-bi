-- 增量：LLM 视觉档案 supports_vision、llm_settings.vision_profile_id
-- mysql -h127.0.0.1 -P3307 -udemo_user -pdemo_pass chatbi_admin < database/migrations/005_llm_vision_settings.sql
-- 若列或约束已存在，可按报错跳过对应语句。

USE chatbi_admin;

ALTER TABLE llm_model_profile
  ADD COLUMN supports_vision TINYINT(1) NOT NULL DEFAULT 0 AFTER sort_order;

ALTER TABLE llm_settings
  ADD COLUMN vision_profile_id BIGINT NULL AFTER active_profile_id;

ALTER TABLE llm_settings
  ADD CONSTRAINT fk_llm_settings_vision_profile FOREIGN KEY (vision_profile_id)
  REFERENCES llm_model_profile (id) ON DELETE SET NULL;
