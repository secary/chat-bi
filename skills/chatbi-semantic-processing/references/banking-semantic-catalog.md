# Banking Semantic Catalog

Use this catalog as seed knowledge. Prefer project-specific metadata if available.

## Business Lines

| business_line | canonical_name | synonyms | typical_subjects |
| --- | --- | --- | --- |
| corporate | 对公业务 | 对公, 公司业务, 企业业务, 单位客户, 机构客户, 对公客户, 公司客户 | 企业客户, 对公账户, 对公存款, 对公贷款, 票据, 现金管理 |
| retail | 个人业务 | 个人, 零售, 私人银行, 个人客户, 储蓄客户, 个人金融 | 个人客户, 储蓄账户, 借记卡, 信用卡, 个贷, 手机银行个人用户 |
| inclusive_finance | 普惠业务 | 普惠, 小微, 普惠金融, 普惠贷款, 小微企业, 个体工商户 | 普惠贷款, 小微客户, 涉农客户 |
| financial_markets | 金融市场业务 | 同业, 金融市场, 资金业务, 票据业务, 债券业务 | 同业客户, 票据, 债券, 拆借 |

## Metric Synonyms

| metric_id | canonical_name | synonyms | domain | default_aggregation | required_context |
| --- | --- | --- | --- | --- | --- |
| deposit_balance | 存款余额 | 存款规模, 存款额, 存款总额, 时点存款, 对公存款余额, 个人存款余额 | deposit | sum | time_range |
| corporate_deposit_balance | 对公存款余额 | 公司存款余额, 企业存款余额, 单位存款余额, 对公存款规模 | deposit | sum | business_line=corporate,time_range |
| retail_deposit_balance | 个人存款余额 | 储蓄存款余额, 零售存款余额, 个人存款规模 | deposit | sum | business_line=retail,time_range |
| avg_daily_deposit_balance | 日均存款余额 | 日均存款, 存款日均, 平均存款余额 | deposit | avg | time_range |
| deposit_growth_amount | 存款较期初增长额 | 存款增量, 存款增长, 较期初新增存款 | deposit | sum | base_period,current_period |
| loan_balance | 贷款余额 | 贷款规模, 信贷余额, 贷款总额, 表内贷款余额 | loan | sum | time_range |
| corporate_loan_balance | 对公贷款余额 | 公司贷款余额, 企业贷款余额, 对公信贷余额, 对公贷款规模 | loan | sum | business_line=corporate,time_range |
| retail_loan_balance | 个人贷款余额 | 个贷余额, 零售贷款余额, 个人消费贷款余额, 按揭贷款余额 | loan | sum | business_line=retail,time_range |
| inclusive_loan_balance | 普惠贷款余额 | 小微贷款余额, 普惠金融贷款余额, 普惠小微贷款余额 | loan | sum | business_line=inclusive_finance,time_range |
| loan_disbursement_amount | 贷款投放金额 | 放款金额, 新发放贷款, 贷款发放额 | loan | sum | time_range |
| corporate_loan_disbursement_amount | 对公贷款投放金额 | 对公放款金额, 企业贷款投放, 公司贷款发放额 | loan | sum | business_line=corporate,time_range |
| retail_loan_disbursement_amount | 个人贷款投放金额 | 个贷投放, 个人放款金额, 零售贷款发放额 | loan | sum | business_line=retail,time_range |
| overdue_loan_balance | 逾期贷款余额 | 逾期余额, 逾期贷款, 逾期本金 | risk | sum | time_range |
| npl_balance | 不良贷款余额 | 不良余额, 不良贷款, 五级分类不良余额 | risk | sum | time_range |
| npl_ratio | 不良贷款率 | 不良率, 贷款不良率 | risk | ratio | time_range, numerator, denominator |
| customer_count | 客户数 | 客户数量, 户数, 客群人数 | customer | count_distinct | time_range |
| corporate_customer_count | 对公客户数 | 企业客户数, 公司客户数, 单位客户数, 对公户数 | customer | count_distinct | business_line=corporate,time_range |
| retail_customer_count | 个人客户数 | 零售客户数, 个人户数, 储蓄客户数 | customer | count_distinct | business_line=retail,time_range |
| new_customer_count | 新增客户数 | 新客户, 拉新客户, 新开户客户数 | customer | count_distinct | time_range |
| new_corporate_customer_count | 新增对公客户数 | 新增企业客户, 新增公司客户, 新开对公户 | customer | count_distinct | business_line=corporate,time_range |
| new_retail_customer_count | 新增个人客户数 | 新增零售客户, 新增个人客户, 新开个人户 | customer | count_distinct | business_line=retail,time_range |
| active_customer_count | 活跃客户数 | 活客数, 动户客户, 交易活跃客户 | customer | count_distinct | time_range, active_rule |
| card_issued_count | 发卡量 | 开卡量, 新发卡数, 发卡张数 | card | count | time_range |
| transaction_amount | 交易金额 | 交易额, 流水金额, 支付金额 | transaction | sum | time_range |
| transaction_count | 交易笔数 | 笔数, 交易次数, 流水笔数 | transaction | count | time_range |
| aum_balance | AUM余额 | 金融资产余额, 管理资产规模, 客户资产余额 | wealth | sum | time_range |
| wealth_product_sales | 理财销售额 | 理财销量, 理财购买金额, 理财产品销售金额 | wealth | sum | time_range |
| fee_income | 中间业务收入 | 手续费收入, 中收, 非息收入 | income | sum | time_range |
| interest_income | 利息收入 | 息收, 贷款利息收入 | income | sum | time_range |
| mobile_active_user_count | 手机银行活跃用户数 | 手机银行活客, MAU, 月活用户, 掌银活跃用户 | channel | count_distinct | time_range, active_rule |
| digital_transaction_amount | 线上交易金额 | 电子渠道交易额, 数字渠道交易金额 | channel | sum | time_range |

## Dimension Synonyms

| dimension_id | canonical_name | synonyms | examples |
| --- | --- | --- | --- |
| business_line | 业务线 | 业务条线, 板块, 对公个人, 公司零售, 条线 | 对公, 个人, 普惠, 金融市场 |
| branch | 机构 | 网点, 分行, 支行, 营业部, 经营机构, 管辖行 | 上海分行, 朝阳支行 |
| region | 地区 | 区域, 省份, 城市, 地市, 行政区 | 华东, 广东, 深圳 |
| customer_type | 客户类型 | 客群, 客户类别, 客户属性 | 个人, 对公, 小微 |
| customer_segment | 客户分层 | 客户等级, 客户层级, 客户分群 | 私行, 财富, 大众 |
| product | 产品 | 产品名称, 产品线, 业务品种 | 定期存款, 经营贷 |
| account_type | 账户类型 | 账户类别, 卡种, 账户性质 | 借记卡, 对公账户 |
| loan_type | 贷款类型 | 贷款品种, 信贷品种 | 按揭贷, 消费贷 |
| deposit_type | 存款类型 | 存款品种 | 活期, 定期, 通知存款 |
| channel | 渠道 | 交易渠道, 办理渠道, 来源渠道 | 柜面, 手机银行, 网银 |
| currency | 币种 | 货币, 交易币种 | CNY, USD |
| risk_level | 风险等级 | 风险分类, 五级分类, 客户风险级别 | 正常, 关注, 次级 |
| employee | 客户经理 | 经理, 经办人, 管户经理 | 张三 |
| industry | 行业 | 客户行业, 国标行业 | 制造业, 房地产 |
| time | 时间 | 日期, 月份, 季度, 年份, 统计期 | 2026-04 |

## Disambiguation Rules

- "规模" may mean balance. Ask whether it is deposit, loan, AUM, or another product if not specified.
- "客户" may mean retail customer, corporate customer, active customer, opened customer, managed customer, account holder, borrower, or cardholder. Ask when the metric depends on the definition.
- "对公" and "个人" are business-line signals. Use them to select business-line-specific metrics when available, such as `corporate_deposit_balance` or `retail_deposit_balance`.
- If a metric has both corporate and retail variants and the utterance does not specify the business line, ask whether to use 对公业务, 个人业务, 普惠业务, or 全行汇总口径.
- Do not collapse `inclusive_finance` into `corporate` unless local reporting rules explicitly define 普惠 as part of 对公.
- "新增" needs a business event: new account, new customer, new card, new loan, or new balance increase.
- "排名" requires metric, entity dimension, period, sort direction, and limit. Default sort direction is descending.
- "同比" compares with the same period in the prior year. "环比" compares with the immediately previous comparable period.
- "余额" is usually a point-in-time metric. If the user gives a month, prefer month-end balance unless local rules say average balance.
