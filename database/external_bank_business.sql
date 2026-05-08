USE chatbi_bank_external;

DROP VIEW IF EXISTS sales_order;
DROP VIEW IF EXISTS customer_profile;
DROP TABLE IF EXISTS risk_event;
DROP TABLE IF EXISTS wealth_position;
DROP TABLE IF EXISTS channel_transaction;
DROP TABLE IF EXISTS card_account;
DROP TABLE IF EXISTS loan_repayment;
DROP TABLE IF EXISTS loan_contract;
DROP TABLE IF EXISTS deposit_daily_balance;
DROP TABLE IF EXISTS customer_account;
DROP TABLE IF EXISTS bank_customer;
DROP TABLE IF EXISTS bank_branch;

CREATE TABLE bank_branch (
  branch_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  branch_name VARCHAR(80) NOT NULL,
  region VARCHAR(50) NOT NULL,
  city VARCHAR(50) NOT NULL,
  branch_level VARCHAR(40) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE bank_customer (
  customer_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  customer_name VARCHAR(80) NOT NULL,
  customer_type VARCHAR(50) NOT NULL,
  risk_level VARCHAR(30) NOT NULL,
  branch_id BIGINT NOT NULL,
  open_date DATE NOT NULL,
  CONSTRAINT fk_customer_branch FOREIGN KEY (branch_id) REFERENCES bank_branch (branch_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE customer_account (
  account_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  customer_id BIGINT NOT NULL,
  account_type VARCHAR(50) NOT NULL,
  status VARCHAR(30) NOT NULL,
  open_date DATE NOT NULL,
  close_date DATE NULL,
  CONSTRAINT fk_account_customer FOREIGN KEY (customer_id) REFERENCES bank_customer (customer_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE deposit_daily_balance (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  stat_date DATE NOT NULL,
  account_id BIGINT NOT NULL,
  product_name VARCHAR(80) NOT NULL,
  balance_amount DECIMAL(14,2) NOT NULL,
  interest_income DECIMAL(12,2) NOT NULL,
  target_balance DECIMAL(14,2) NOT NULL,
  CONSTRAINT fk_deposit_account FOREIGN KEY (account_id) REFERENCES customer_account (account_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE loan_contract (
  loan_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  customer_id BIGINT NOT NULL,
  branch_id BIGINT NOT NULL,
  product_name VARCHAR(80) NOT NULL,
  loan_amount DECIMAL(14,2) NOT NULL,
  outstanding_amount DECIMAL(14,2) NOT NULL,
  interest_income DECIMAL(12,2) NOT NULL,
  loan_date DATE NOT NULL,
  risk_status VARCHAR(40) NOT NULL,
  CONSTRAINT fk_loan_customer FOREIGN KEY (customer_id) REFERENCES bank_customer (customer_id),
  CONSTRAINT fk_loan_branch FOREIGN KEY (branch_id) REFERENCES bank_branch (branch_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE loan_repayment (
  repayment_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  loan_id BIGINT NOT NULL,
  repay_date DATE NOT NULL,
  principal_amount DECIMAL(14,2) NOT NULL,
  interest_amount DECIMAL(12,2) NOT NULL,
  overdue_days INT NOT NULL,
  CONSTRAINT fk_repayment_loan FOREIGN KEY (loan_id) REFERENCES loan_contract (loan_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE card_account (
  card_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  customer_id BIGINT NOT NULL,
  branch_id BIGINT NOT NULL,
  card_type VARCHAR(40) NOT NULL,
  credit_limit DECIMAL(12,2) NOT NULL,
  outstanding_amount DECIMAL(12,2) NOT NULL,
  active_flag TINYINT(1) NOT NULL,
  CONSTRAINT fk_card_customer FOREIGN KEY (customer_id) REFERENCES bank_customer (customer_id),
  CONSTRAINT fk_card_branch FOREIGN KEY (branch_id) REFERENCES bank_branch (branch_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE channel_transaction (
  transaction_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  transaction_date DATE NOT NULL,
  customer_id BIGINT NOT NULL,
  channel VARCHAR(50) NOT NULL,
  transaction_type VARCHAR(50) NOT NULL,
  transaction_amount DECIMAL(14,2) NOT NULL,
  fee_income DECIMAL(12,2) NOT NULL,
  CONSTRAINT fk_tx_customer FOREIGN KEY (customer_id) REFERENCES bank_customer (customer_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE wealth_position (
  position_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  stat_date DATE NOT NULL,
  customer_id BIGINT NOT NULL,
  product_name VARCHAR(80) NOT NULL,
  product_category VARCHAR(50) NOT NULL,
  aum_amount DECIMAL(14,2) NOT NULL,
  fee_income DECIMAL(12,2) NOT NULL,
  CONSTRAINT fk_wealth_customer FOREIGN KEY (customer_id) REFERENCES bank_customer (customer_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE risk_event (
  event_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  event_date DATE NOT NULL,
  customer_id BIGINT NOT NULL,
  branch_id BIGINT NOT NULL,
  event_type VARCHAR(50) NOT NULL,
  risk_level VARCHAR(30) NOT NULL,
  exposure_amount DECIMAL(14,2) NOT NULL,
  resolved_flag TINYINT(1) NOT NULL,
  CONSTRAINT fk_risk_customer FOREIGN KEY (customer_id) REFERENCES bank_customer (customer_id),
  CONSTRAINT fk_risk_branch FOREIGN KEY (branch_id) REFERENCES bank_branch (branch_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO bank_branch (branch_name, region, city, branch_level) VALUES
('上海浦东支行', '华东', '上海', '一级支行'),
('广州天河支行', '华南', '广州', '一级支行'),
('北京朝阳支行', '华北', '北京', '一级支行'),
('成都高新支行', '西南', '成都', '一级支行');

INSERT INTO bank_customer (customer_name, customer_type, risk_level, branch_id, open_date) VALUES
('海岳制造集团', '对公客户', '中低风险', 1, '2023-03-18'),
('南湾零售连锁', '小微客户', '中风险', 2, '2024-06-20'),
('北辰科技有限公司', '对公客户', '低风险', 3, '2022-11-08'),
('锦城个人客户群', '个人客户', '中低风险', 4, '2025-01-16'),
('浦江高净值客户', '个人客户', '低风险', 1, '2024-02-02'),
('华南跨境贸易', '对公客户', '中风险', 2, '2023-09-12');

INSERT INTO customer_account (customer_id, account_type, status, open_date, close_date) VALUES
(1, '对公活期账户', '正常', '2023-03-18', NULL),
(2, '小微结算账户', '正常', '2024-06-20', NULL),
(3, '对公定期账户', '正常', '2022-11-08', NULL),
(4, '个人储蓄账户', '正常', '2025-01-16', NULL),
(5, '私人银行账户', '正常', '2024-02-02', NULL),
(6, '跨境结算账户', '正常', '2023-09-12', NULL);

INSERT INTO deposit_daily_balance (stat_date, account_id, product_name, balance_amount, interest_income, target_balance) VALUES
('2026-01-31', 1, '对公活期存款', 15800000, 18200, 15000000), ('2026-02-28', 1, '对公活期存款', 17100000, 19700, 16000000),
('2026-03-31', 1, '对公活期存款', 18800000, 21600, 17000000), ('2026-04-30', 1, '对公活期存款', 19400000, 22900, 18000000),
('2026-01-31', 3, '结构性存款', 12600000, 42600, 12000000), ('2026-02-28', 3, '结构性存款', 13200000, 44800, 12500000),
('2026-03-31', 5, '大额存单', 9200000, 31800, 9000000), ('2026-04-30', 5, '大额存单', 9800000, 33700, 9300000);

INSERT INTO loan_contract (customer_id, branch_id, product_name, loan_amount, outstanding_amount, interest_income, loan_date, risk_status) VALUES
(1, 1, '流动资金贷款', 12000000, 9800000, 156000, '2026-01-10', '正常'),
(2, 2, '普惠小微贷款', 2600000, 2100000, 43800, '2026-02-14', '关注'),
(3, 3, '科技企业信用贷', 8600000, 7900000, 119000, '2026-03-08', '正常'),
(6, 2, '贸易融资', 6800000, 5200000, 91000, '2026-04-12', '关注');

INSERT INTO loan_repayment (loan_id, repay_date, principal_amount, interest_amount, overdue_days) VALUES
(1, '2026-03-21', 900000, 39200, 0), (1, '2026-04-21', 900000, 37800, 0),
(2, '2026-04-18', 180000, 9600, 5), (3, '2026-04-20', 350000, 28400, 0),
(4, '2026-04-25', 420000, 21600, 3);

INSERT INTO card_account (customer_id, branch_id, card_type, credit_limit, outstanding_amount, active_flag) VALUES
(4, 4, '信用卡金卡', 80000, 23800, 1), (5, 1, '白金信用卡', 300000, 87500, 1),
(2, 2, '商务卡', 150000, 62000, 1), (3, 3, '企业公务卡', 200000, 41000, 1);

INSERT INTO channel_transaction (transaction_date, customer_id, channel, transaction_type, transaction_amount, fee_income) VALUES
('2026-01-15', 1, '网银', '转账结算', 5200000, 2200), ('2026-02-16', 2, '手机银行', '贷款还款', 210000, 680),
('2026-03-18', 3, '柜面', '定期开户', 3000000, 1200), ('2026-03-22', 5, '私人银行', '理财申购', 1800000, 9000),
('2026-04-08', 6, '跨境金融', '信用证', 2600000, 15800), ('2026-04-19', 4, '手机银行', '消费支付', 68000, 520);

INSERT INTO wealth_position (stat_date, customer_id, product_name, product_category, aum_amount, fee_income) VALUES
('2026-01-31', 5, '稳健固收理财', '理财', 5200000, 12800), ('2026-02-28', 5, '稳健固收理财', '理财', 5600000, 13900),
('2026-03-31', 4, '养老目标基金', '基金', 860000, 2400), ('2026-04-30', 5, '私人银行组合', '财富管理', 7200000, 23600);

INSERT INTO risk_event (event_date, customer_id, branch_id, event_type, risk_level, exposure_amount, resolved_flag) VALUES
('2026-02-20', 2, 2, '还款逾期', '中风险', 2100000, 0),
('2026-04-17', 6, 2, '贸易背景核验', '中风险', 5200000, 0),
('2026-04-24', 4, 4, '异常交易预警', '低风险', 68000, 1);

CREATE VIEW sales_order AS
SELECT d.stat_date AS order_date, b.region, b.branch_name AS department, '存款业务' AS product_category,
       d.product_name, '网点' AS channel, c.customer_type, d.balance_amount AS sales_amount,
       1 AS order_count, 1 AS customer_count, d.interest_income AS gross_profit, d.target_balance AS target_amount
FROM deposit_daily_balance d
JOIN customer_account a ON d.account_id = a.account_id
JOIN bank_customer c ON a.customer_id = c.customer_id
JOIN bank_branch b ON c.branch_id = b.branch_id
UNION ALL
SELECT l.loan_date, b.region, b.branch_name, '贷款业务', l.product_name, '客户经理', c.customer_type,
       l.outstanding_amount, 1, 1, l.interest_income, l.loan_amount
FROM loan_contract l
JOIN bank_customer c ON l.customer_id = c.customer_id
JOIN bank_branch b ON l.branch_id = b.branch_id
UNION ALL
SELECT w.stat_date, b.region, b.branch_name, w.product_category, w.product_name, '财富顾问', c.customer_type,
       w.aum_amount, 1, 1, w.fee_income, w.aum_amount
FROM wealth_position w
JOIN bank_customer c ON w.customer_id = c.customer_id
JOIN bank_branch b ON c.branch_id = b.branch_id;

CREATE VIEW customer_profile AS
SELECT DATE_FORMAT(c.open_date, '%Y-%m-01') AS stat_month, b.region, c.customer_type,
       COUNT(*) AS new_customers,
       SUM(CASE WHEN a.status = '正常' THEN 1 ELSE 0 END) AS active_customers,
       SUM(CASE WHEN a.status = '正常' THEN 1 ELSE 0 END) AS retained_customers,
       SUM(CASE WHEN a.status <> '正常' THEN 1 ELSE 0 END) AS churned_customers
FROM bank_customer c
JOIN bank_branch b ON c.branch_id = b.branch_id
LEFT JOIN customer_account a ON c.customer_id = a.customer_id
GROUP BY DATE_FORMAT(c.open_date, '%Y-%m-01'), b.region, c.customer_type;
