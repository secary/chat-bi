SET NAMES utf8mb4;

CREATE DATABASE IF NOT EXISTS chatbi_demo
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

GRANT ALL PRIVILEGES ON chatbi_demo.* TO 'demo_user'@'%';

USE chatbi_demo;

-- ============================================================
-- 业务数据表
-- ============================================================

CREATE TABLE sales_order (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  order_date DATE NOT NULL,
  region VARCHAR(50) NOT NULL,
  department VARCHAR(50) NOT NULL,
  product_category VARCHAR(50) NOT NULL,
  product_name VARCHAR(80) NOT NULL,
  channel VARCHAR(50) NOT NULL,
  customer_type VARCHAR(50) NOT NULL,
  sales_amount DECIMAL(12,2) NOT NULL,
  order_count INT NOT NULL,
  customer_count INT NOT NULL,
  gross_profit DECIMAL(12,2) NOT NULL,
  target_amount DECIMAL(12,2) NOT NULL
);

CREATE TABLE customer_profile (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  stat_month DATE NOT NULL,
  region VARCHAR(50) NOT NULL,
  customer_type VARCHAR(50) NOT NULL,
  new_customers INT NOT NULL,
  active_customers INT NOT NULL,
  retained_customers INT NOT NULL,
  churned_customers INT NOT NULL
);

INSERT INTO sales_order
(order_date, region, department, product_category, product_name, channel, customer_type, sales_amount, order_count, customer_count, gross_profit, target_amount)
VALUES
('2026-01-05', '华东', '商业增长部', '软件服务', '智能分析平台', '线上', '企业客户', 128000, 36, 30, 44800, 120000),
('2026-01-08', '华南', '数据产品部', '数据产品', '指标治理套件', '渠道', '企业客户', 86000, 24, 20, 30100, 90000),
('2026-01-15', '华北', '咨询服务部', '咨询服务', '数据治理咨询', '直销', '中小客户', 76000, 18, 16, 24300, 70000),
('2026-01-22', '西南', '商业增长部', '软件服务', 'ChatBI 助手', '直销', '中小客户', 65000, 15, 14, 22100, 68000),
('2026-02-06', '华东', '商业增长部', '软件服务', '智能分析平台', '线上', '企业客户', 145000, 41, 34, 52200, 130000),
('2026-02-13', '华南', '数据产品部', '数据产品', '指标治理套件', '渠道', '企业客户', 98000, 27, 23, 35200, 95000),
('2026-02-18', '华北', '咨询服务部', '咨询服务', '数据治理咨询', '直销', '中小客户', 69000, 16, 15, 20700, 76000),
('2026-02-25', '西南', '商业增长部', '软件服务', 'ChatBI 助手', '线上', '中小客户', 82000, 21, 18, 29500, 72000),
('2026-03-04', '华东', '商业增长部', '软件服务', '智能分析平台', '渠道', '企业客户', 168000, 46, 39, 62100, 145000),
('2026-03-11', '华南', '数据产品部', '数据产品', '指标治理套件', '线上', '企业客户', 116000, 32, 28, 42900, 105000),
('2026-03-19', '华北', '咨询服务部', '咨询服务', '数据治理咨询', '直销', '中小客户', 84000, 22, 19, 26000, 80000),
('2026-03-28', '西南', '商业增长部', '软件服务', 'ChatBI 助手', '线上', '中小客户', 74000, 18, 16, 25100, 78000),
('2026-04-03', '华东', '商业增长部', '软件服务', '智能分析平台', '线上', '企业客户', 172000, 48, 41, 63600, 160000),
('2026-04-10', '华南', '数据产品部', '数据产品', '指标治理套件', '渠道', '企业客户', 102000, 29, 24, 36700, 112000),
('2026-04-17', '华北', '咨询服务部', '咨询服务', '数据治理咨询', '直销', '中小客户', 92000, 24, 21, 29400, 86000),
('2026-04-24', '西南', '商业增长部', '软件服务', 'ChatBI 助手', '线上', '中小客户', 96000, 25, 22, 34500, 82000);

INSERT INTO customer_profile
(stat_month, region, customer_type, new_customers, active_customers, retained_customers, churned_customers)
VALUES
('2026-01-01', '华东', '企业客户', 18, 126, 108, 7),
('2026-01-01', '华南', '企业客户', 14, 98, 82, 8),
('2026-01-01', '华北', '中小客户', 11, 76, 63, 6),
('2026-01-01', '西南', '中小客户', 9, 68, 55, 7),
('2026-02-01', '华东', '企业客户', 22, 141, 121, 6),
('2026-02-01', '华南', '企业客户', 17, 109, 91, 7),
('2026-02-01', '华北', '中小客户', 10, 80, 66, 9),
('2026-02-01', '西南', '中小客户', 13, 75, 61, 5),
('2026-03-01', '华东', '企业客户', 25, 158, 137, 5),
('2026-03-01', '华南', '企业客户', 19, 121, 103, 6),
('2026-03-01', '华北', '中小客户', 14, 88, 73, 7),
('2026-03-01', '西南', '中小客户', 12, 82, 68, 6),
('2026-04-01', '华东', '企业客户', 21, 171, 149, 8),
('2026-04-01', '华南', '企业客户', 16, 128, 110, 9),
('2026-04-01', '华北', '中小客户', 15, 96, 80, 6),
('2026-04-01', '西南', '中小客户', 14, 92, 77, 5);

-- ============================================================
-- 语义层元数据表
-- ============================================================

DROP TABLE IF EXISTS alias_mapping;
DROP TABLE IF EXISTS business_term;
DROP TABLE IF EXISTS dimension_definition;
DROP TABLE IF EXISTS metric_definition;
DROP TABLE IF EXISTS field_dictionary;
DROP TABLE IF EXISTS data_source_config;

CREATE TABLE data_source_config (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  source_name VARCHAR(80) NOT NULL,
  source_type VARCHAR(40) NOT NULL,
  connection_name VARCHAR(80) NOT NULL,
  database_name VARCHAR(80) NOT NULL,
  table_name VARCHAR(80) NOT NULL,
  refresh_mode VARCHAR(40) NOT NULL,
  owner_name VARCHAR(50) NOT NULL,
  description VARCHAR(255) NOT NULL
);

CREATE TABLE field_dictionary (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  table_name VARCHAR(80) NOT NULL,
  field_name VARCHAR(80) NOT NULL,
  field_type VARCHAR(40) NOT NULL,
  business_name VARCHAR(80) NOT NULL,
  business_meaning VARCHAR(255) NOT NULL,
  example_value VARCHAR(80) NOT NULL
);

CREATE TABLE metric_definition (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  metric_name VARCHAR(80) NOT NULL,
  metric_code VARCHAR(80) NOT NULL,
  source_table VARCHAR(80) NOT NULL,
  formula VARCHAR(255) NOT NULL,
  business_caliber VARCHAR(255) NOT NULL,
  default_dimensions VARCHAR(255) NOT NULL
);

CREATE TABLE dimension_definition (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  dimension_name VARCHAR(80) NOT NULL,
  field_name VARCHAR(80) NOT NULL,
  source_table VARCHAR(80) NOT NULL,
  description VARCHAR(255) NOT NULL
);

CREATE TABLE business_term (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  term_name VARCHAR(80) NOT NULL,
  term_type VARCHAR(40) NOT NULL,
  definition VARCHAR(255) NOT NULL,
  related_metric VARCHAR(80) NOT NULL
);

CREATE TABLE alias_mapping (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  alias_name VARCHAR(80) NOT NULL,
  standard_name VARCHAR(80) NOT NULL,
  object_type VARCHAR(40) NOT NULL,
  description VARCHAR(255) NOT NULL
);

INSERT INTO data_source_config
(source_name, source_type, connection_name, database_name, table_name, refresh_mode, owner_name, description)
VALUES
('演示销售订单数据源', 'MySQL', 'chatbi_demo_mysql', 'chatbi_demo', 'sales_order', '每日自动同步', '数据产品部', '用于演示销售、渠道、区域、产品和目标完成情况分析'),
('演示客户画像数据源', 'MySQL', 'chatbi_demo_mysql', 'chatbi_demo', 'customer_profile', '每月自动同步', '数据产品部', '用于演示客户新增、活跃、留存和流失分析');

INSERT INTO field_dictionary
(table_name, field_name, field_type, business_name, business_meaning, example_value)
VALUES
('sales_order', 'order_date', 'DATE', '订单日期', '订单发生日期，可用于按日、月、季度统计趋势', '2026-04-03'),
('sales_order', 'region', 'VARCHAR', '区域', '业务所属区域，用于区域对比和区域下钻', '华东'),
('sales_order', 'department', 'VARCHAR', '部门', '负责该笔业务的组织部门', '商业增长部'),
('sales_order', 'product_category', 'VARCHAR', '产品类别', '产品所属业务分类', '软件服务'),
('sales_order', 'product_name', 'VARCHAR', '产品名称', '具体产品或服务名称', '智能分析平台'),
('sales_order', 'channel', 'VARCHAR', '渠道', '成交来源渠道', '线上'),
('sales_order', 'customer_type', 'VARCHAR', '客户类型', '客户分层类型', '企业客户'),
('sales_order', 'sales_amount', 'DECIMAL', '销售额', '订单确认收入金额', '172000.00'),
('sales_order', 'order_count', 'INT', '订单数', '订单数量', '48'),
('sales_order', 'customer_count', 'INT', '客户数', '产生订单的客户数量', '41'),
('sales_order', 'gross_profit', 'DECIMAL', '毛利', '销售额扣除直接成本后的利润', '63600.00'),
('sales_order', 'target_amount', 'DECIMAL', '目标销售额', '用于计算目标完成率的计划值', '160000.00'),
('customer_profile', 'new_customers', 'INT', '新增客户数', '统计周期内首次产生业务关系的客户数', '21'),
('customer_profile', 'active_customers', 'INT', '活跃客户数', '统计周期内有有效互动或交易的客户数', '171'),
('customer_profile', 'retained_customers', 'INT', '留存客户数', '上期客户在本期仍保持活跃的数量', '149'),
('customer_profile', 'churned_customers', 'INT', '流失客户数', '统计周期内从活跃转为非活跃的客户数量', '8');

INSERT INTO metric_definition
(metric_name, metric_code, source_table, formula, business_caliber, default_dimensions)
VALUES
('销售额', 'sales_amount', 'sales_order', 'SUM(sales_amount)', '统计周期内订单确认收入总额', '时间、区域、部门、产品类别、渠道'),
('订单数', 'order_count', 'sales_order', 'SUM(order_count)', '统计周期内订单数量合计', '时间、区域、部门、产品类别、渠道'),
('客户数', 'customer_count', 'sales_order', 'SUM(customer_count)', '统计周期内产生订单的客户数量合计', '时间、区域、客户类型'),
('毛利', 'gross_profit', 'sales_order', 'SUM(gross_profit)', '销售额扣除直接成本后的利润合计', '时间、区域、产品类别'),
('毛利率', 'gross_profit_rate', 'sales_order', 'SUM(gross_profit) / SUM(sales_amount)', '衡量业务盈利能力，销售额为 0 时不计算', '时间、区域、产品类别、渠道'),
('目标完成率', 'target_achievement_rate', 'sales_order', 'SUM(sales_amount) / SUM(target_amount)', '实际销售额相对于目标销售额的完成比例', '时间、区域、部门'),
('新增客户数', 'new_customers', 'customer_profile', 'SUM(new_customers)', '统计周期内新增客户数量', '月份、区域、客户类型'),
('客户留存率', 'retention_rate', 'customer_profile', 'SUM(retained_customers) / SUM(active_customers)', '留存客户数占活跃客户数的比例', '月份、区域、客户类型');

INSERT INTO dimension_definition
(dimension_name, field_name, source_table, description)
VALUES
('时间', 'order_date', 'sales_order', '支持按日、月、季度、年度聚合'),
('区域', 'region', 'sales_order', '支持华东、华南、华北、西南等区域对比'),
('部门', 'department', 'sales_order', '支持按组织部门查看业务表现'),
('产品类别', 'product_category', 'sales_order', '支持软件服务、数据产品、咨询服务等分类分析'),
('产品名称', 'product_name', 'sales_order', '支持具体产品下钻'),
('渠道', 'channel', 'sales_order', '支持线上、渠道、直销等来源分析'),
('客户类型', 'customer_type', 'sales_order', '支持企业客户、中小客户等客户分层分析');

INSERT INTO business_term
(term_name, term_type, definition, related_metric)
VALUES
('经营概览', '业务场景', '面向管理层展示销售、客户、目标完成和趋势变化的综合视图', '销售额'),
('目标完成', '分析主题', '对比实际销售额与目标销售额，识别未达标区域或部门', '目标完成率'),
('异常波动', '分析主题', '识别指标在时间序列中的突增、突降和偏离趋势情况', '销售额'),
('归因分析', '分析方法', '从区域、产品、渠道、客户类型等维度拆解指标变化原因', '销售额'),
('客户留存', '分析主题', '衡量客户持续活跃情况，辅助判断客户运营质量', '客户留存率');

INSERT INTO alias_mapping
(alias_name, standard_name, object_type, description)
VALUES
('收入', '销售额', '指标', '用户问收入时默认映射到销售额'),
('成交额', '销售额', '指标', '成交金额、成交额统一映射到销售额'),
('利润', '毛利', '指标', '演示环境中利润默认使用毛利口径'),
('完成情况', '目标完成率', '指标', '用于回答目标完成、达成率相关问题'),
('复购', '客户留存率', '指标', '复购、留存类问题默认映射到客户留存率'),
('大区', '区域', '维度', '大区、地区统一映射到区域维度'),
('地区', '区域', '维度', '地区统一映射到区域维度'),
('片区', '区域', '维度', '片区统一映射到区域维度'),
('市场', '区域', '维度', '市场统一映射到区域维度'),
('业务区域', '区域', '维度', '业务区域统一映射到区域维度'),
('团队', '部门', '维度', '团队统一映射到部门维度'),
('组织', '部门', '维度', '组织统一映射到部门维度'),
('业务部门', '部门', '维度', '业务部门统一映射到部门维度'),
('产品线', '产品类别', '维度', '产品线、品类统一映射到产品类别'),
('品类', '产品类别', '维度', '品类统一映射到产品类别维度'),
('业务线', '产品类别', '维度', '业务线统一映射到产品类别维度'),
('产品类型', '产品类别', '维度', '产品类型统一映射到产品类别维度'),
('产品分类', '产品类别', '维度', '产品分类统一映射到产品类别维度'),
('产品名', '产品名称', '维度', '产品名统一映射到产品名称维度'),
('具体产品', '产品名称', '维度', '具体产品统一映射到产品名称维度'),
('服务名称', '产品名称', '维度', '服务名称统一映射到产品名称维度'),
('来源', '渠道', '维度', '来源统一映射到渠道维度'),
('成交来源', '渠道', '维度', '成交来源统一映射到渠道维度'),
('成交渠道', '渠道', '维度', '成交渠道统一映射到渠道维度'),
('获客渠道', '渠道', '维度', '获客渠道统一映射到渠道维度'),
('销售渠道', '渠道', '维度', '销售渠道统一映射到渠道维度'),
('业务来源', '渠道', '维度', '业务来源统一映射到渠道维度'),
('客群', '客户类型', '维度', '客群统一映射到客户类型维度'),
('客户群', '客户类型', '维度', '客户群统一映射到客户类型维度'),
('客户类别', '客户类型', '维度', '客户类别统一映射到客户类型维度'),
('客户分层', '客户类型', '维度', '客户分层统一映射到客户类型维度'),
('客户层级', '客户类型', '维度', '客户层级统一映射到客户类型维度'),
('客户结构', '客户类型', '维度', '客户结构统一映射到客户类型维度'),
('日期', '时间', '维度', '日期统一映射到时间维度'),
('月份', '时间', '维度', '月份统一映射到时间维度'),
('月度', '时间', '维度', '月度统一映射到时间维度'),
('每月', '时间', '维度', '每月统一映射到时间维度'),
('时间趋势', '时间', '维度', '时间趋势统一映射到时间维度');

-- ============================================================
-- 应用表：前端登录、会话、记忆、配置、日志
-- ============================================================

DROP TABLE IF EXISTS chatbi_app_user_memory;
DROP TABLE IF EXISTS chatbi_app_chat_message;
DROP TABLE IF EXISTS chatbi_app_chat_session;
DROP TABLE IF EXISTS chatbi_logs_trace_log;
DROP TABLE IF EXISTS chatbi_admin_llm_settings;
DROP TABLE IF EXISTS chatbi_admin_llm_model_profile;
DROP TABLE IF EXISTS chatbi_admin_app_db_connection;
DROP TABLE IF EXISTS chatbi_admin_skill_registry;
DROP TABLE IF EXISTS chatbi_app_user;

CREATE TABLE chatbi_app_user (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(120) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(32) NOT NULL DEFAULT 'user',
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  UNIQUE KEY uq_app_user_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 默认管理员 admin / admin123（部署后请修改）
INSERT INTO chatbi_app_user (username, password_hash, role, is_active)
VALUES (
  'admin',
  '$2b$12$iXi5Jzd4MR2HPoWaaai6pOmuDcivD9AF05G.knPmpp7Gp5drrSVYG',
  'admin',
  1
);

CREATE TABLE chatbi_app_chat_session (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(255) NOT NULL DEFAULT '新对话',
  user_id BIGINT NOT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  CONSTRAINT fk_chatbi_app_chat_session_user FOREIGN KEY (user_id) REFERENCES chatbi_app_user (id),
  KEY idx_chat_session_updated (updated_at),
  KEY idx_chat_session_user_updated (user_id, updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE chatbi_app_chat_message (
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

CREATE TABLE chatbi_app_user_memory (
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

-- ============================================================
-- 应用配置表：数据源连接、LLM 配置、技能开关、日志
-- ============================================================

CREATE TABLE chatbi_admin_skill_registry (
  skill_slug VARCHAR(128) PRIMARY KEY,
  enabled TINYINT(1) NOT NULL DEFAULT 1,
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE chatbi_admin_app_db_connection (
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

CREATE TABLE chatbi_admin_llm_model_profile (
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

CREATE TABLE chatbi_admin_llm_settings (
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

INSERT INTO chatbi_admin_llm_settings (id, model, api_base, api_key, active_profile_id, vision_profile_id)
VALUES (1, NULL, NULL, NULL, NULL, NULL)
ON DUPLICATE KEY UPDATE id = id;

CREATE TABLE chatbi_logs_trace_log (
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
