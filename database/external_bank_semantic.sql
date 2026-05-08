USE chatbi_bank_external;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE field_dictionary (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  table_name VARCHAR(80) NOT NULL,
  field_name VARCHAR(80) NOT NULL,
  field_type VARCHAR(40) NOT NULL,
  business_name VARCHAR(80) NOT NULL,
  business_meaning VARCHAR(255) NOT NULL,
  example_value VARCHAR(80) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE metric_definition (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  metric_name VARCHAR(80) NOT NULL,
  metric_code VARCHAR(80) NOT NULL,
  source_table VARCHAR(80) NOT NULL,
  formula VARCHAR(255) NOT NULL,
  business_caliber VARCHAR(255) NOT NULL,
  default_dimensions VARCHAR(255) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE dimension_definition (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  dimension_name VARCHAR(80) NOT NULL,
  field_name VARCHAR(80) NOT NULL,
  source_table VARCHAR(80) NOT NULL,
  description VARCHAR(255) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE business_term (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  term_name VARCHAR(80) NOT NULL,
  term_type VARCHAR(40) NOT NULL,
  definition VARCHAR(255) NOT NULL,
  related_metric VARCHAR(80) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE alias_mapping (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  alias_name VARCHAR(80) NOT NULL,
  standard_name VARCHAR(80) NOT NULL,
  object_type VARCHAR(40) NOT NULL,
  description VARCHAR(255) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO data_source_config VALUES
(1, '外部银行经营兼容视图', 'MySQL', 'bank_external_mysql', 'chatbi_bank_external', 'sales_order', '每日同步', '银行数据平台', '由存款、贷款、财富管理明细汇总出的 ChatBI 兼容经营视图'),
(2, '外部银行客户画像视图', 'MySQL', 'bank_external_mysql', 'chatbi_bank_external', 'customer_profile', '每日同步', '银行数据平台', '由客户、账户和网点数据汇总出的客户活跃视图'),
(3, '外部银行贷款明细', 'MySQL', 'bank_external_mysql', 'chatbi_bank_external', 'loan_contract', '实时同步', '信贷管理部', '用于贷款余额、风险状态和利息收入分析');

INSERT INTO field_dictionary (table_name, field_name, field_type, business_name, business_meaning, example_value) VALUES
('sales_order', 'order_date', 'DATE', '业务日期', '存款余额日、贷款发放日或财富持仓日', '2026-04-30'),
('sales_order', 'region', 'VARCHAR', '区域', '分支机构所属区域', '华东'),
('sales_order', 'department', 'VARCHAR', '网点', '承办支行或经营机构', '上海浦东支行'),
('sales_order', 'product_category', 'VARCHAR', '业务类型', '存款业务、贷款业务、财富管理等业务分类', '贷款业务'),
('sales_order', 'product_name', 'VARCHAR', '金融产品', '具体银行产品名称', '流动资金贷款'),
('sales_order', 'channel', 'VARCHAR', '办理渠道', '网点、客户经理、财富顾问等渠道', '客户经理'),
('sales_order', 'customer_type', 'VARCHAR', '客群', '对公、小微、个人等客户分层', '对公客户'),
('sales_order', 'sales_amount', 'DECIMAL', '业务余额', '用于兼容销售额口径的余额/AUM/贷款余额', '19400000.00'),
('sales_order', 'gross_profit', 'DECIMAL', '收入贡献', '存款利息贡献、贷款利息收入或中收', '22900.00'),
('sales_order', 'target_amount', 'DECIMAL', '目标余额', '用于目标完成率计算的计划余额', '18000000.00'),
('customer_profile', 'active_customers', 'INT', '活跃客户数', '正常账户对应的活跃客户数', '1'),
('loan_contract', 'risk_status', 'VARCHAR', '贷款风险状态', '正常、关注等信贷风险分类', '关注');

INSERT INTO metric_definition (metric_name, metric_code, source_table, formula, business_caliber, default_dimensions) VALUES
('销售额', 'sales_amount', 'sales_order', 'SUM(sales_amount)', '兼容 ChatBI 的综合业务规模，银行场景中表示存款余额、贷款余额和财富 AUM 合计', '时间、区域、部门、产品类别、渠道、客户类型'),
('业务规模', 'business_balance', 'sales_order', 'SUM(sales_amount)', '银行经营规模口径，含存款余额、贷款余额、财富 AUM', '时间、区域、产品类别、客户类型'),
('毛利', 'gross_profit', 'sales_order', 'SUM(gross_profit)', '银行收入贡献口径，含利息收入和手续费收入', '时间、区域、产品类别、渠道'),
('毛利率', 'gross_profit_rate', 'sales_order', 'SUM(gross_profit) / SUM(sales_amount)', '收入贡献与业务规模的比率', '时间、区域、产品类别'),
('目标完成率', 'target_achievement_rate', 'sales_order', 'SUM(sales_amount) / SUM(target_amount)', '实际业务规模相对于计划目标的完成比例', '时间、区域、部门'),
('客户数', 'customer_count', 'sales_order', 'SUM(customer_count)', '产生有效余额或持仓的客户数量', '时间、区域、客户类型'),
('订单数', 'order_count', 'sales_order', 'SUM(order_count)', '兼容 ChatBI 的业务记录数量', '时间、区域、产品类别'),
('新增客户数', 'new_customers', 'customer_profile', 'SUM(new_customers)', '统计周期内新开户客户数量', '月份、区域、客户类型'),
('客户留存率', 'retention_rate', 'customer_profile', 'SUM(retained_customers) / SUM(active_customers)', '正常账户客户中持续活跃客户占比', '月份、区域、客户类型');

INSERT INTO dimension_definition (dimension_name, field_name, source_table, description) VALUES
('时间', 'order_date', 'sales_order', '业务发生日期，支持按日、月、季度聚合'),
('区域', 'region', 'sales_order', '华东、华南、华北、西南等经营区域'),
('部门', 'department', 'sales_order', '银行支行或经营机构'),
('产品类别', 'product_category', 'sales_order', '存款业务、贷款业务、财富管理等银行业务类型'),
('产品名称', 'product_name', 'sales_order', '具体金融产品'),
('渠道', 'channel', 'sales_order', '网点、客户经理、手机银行、财富顾问等渠道'),
('客户类型', 'customer_type', 'sales_order', '对公客户、小微客户、个人客户等客群'),
('月份', 'stat_month', 'customer_profile', '客户画像统计月份'),
('区域', 'region', 'customer_profile', '客户所属区域'),
('客户类型', 'customer_type', 'customer_profile', '客户分层');

INSERT INTO business_term (term_name, term_type, definition, related_metric) VALUES
('银行经营概览', '业务场景', '观察存款、贷款、财富管理和客户活跃的综合经营表现', '业务规模'),
('存贷款经营', '分析主题', '按区域、网点、客群拆解存贷款余额与收入贡献', '业务规模'),
('信贷风险', '分析主题', '关注贷款逾期、风险事件和敞口变化', '目标完成率'),
('客户经营', '分析主题', '观察开户、活跃、留存和客群结构', '客户留存率');

INSERT INTO alias_mapping (alias_name, standard_name, object_type, description) VALUES
('余额', '销售额', '指标', '银行场景中余额映射到兼容销售额口径'),
('业务余额', '销售额', '指标', '业务余额映射到综合业务规模'),
('AUM', '销售额', '指标', '财富 AUM 映射到综合业务规模'),
('存款余额', '销售额', '指标', '存款余额按业务规模分析'),
('贷款余额', '销售额', '指标', '贷款余额按业务规模分析'),
('业务规模', '销售额', '指标', '业务规模复用兼容口径'),
('收入贡献', '毛利', '指标', '银行收入贡献映射到毛利'),
('利息收入', '毛利', '指标', '利息收入映射到收入贡献'),
('手续费收入', '毛利', '指标', '手续费收入映射到收入贡献'),
('达成率', '目标完成率', '指标', '目标达成率映射到目标完成率'),
('留存', '客户留存率', '指标', '客户留存映射到客户留存率'),
('网点', '部门', '维度', '网点映射到部门维度'),
('支行', '部门', '维度', '支行映射到部门维度'),
('机构', '部门', '维度', '机构映射到部门维度'),
('业务类型', '产品类别', '维度', '业务类型映射到产品类别'),
('金融产品', '产品名称', '维度', '金融产品映射到产品名称'),
('客群', '客户类型', '维度', '客群映射到客户类型'),
('地区', '区域', '维度', '地区映射到区域'),
('月份', '时间', '维度', '月份映射到时间'),
('办理渠道', '渠道', '维度', '办理渠道映射到渠道');
