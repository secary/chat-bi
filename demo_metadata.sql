SET NAMES utf8mb4;

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
('产品线', '产品类别', '维度', '产品线、品类统一映射到产品类别');
