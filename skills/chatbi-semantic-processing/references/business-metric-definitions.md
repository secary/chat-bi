# Business Metric Definitions

Use these definitions to make semantic parsing stable before Text-to-SQL. Prefer bank-specific metadata when available.

## Definition Fields

- `metric_id`: canonical metric ID from `banking-semantic-catalog.md`.
- `business_line`: `corporate`, `retail`, `inclusive_finance`, `financial_markets`, or `all`.
- `grain`: lowest reliable calculation grain, such as customer, account, contract, card, transaction, organization, or day.
- `snapshot_type`: point-in-time or period metric semantics.
- `formula`: business calculation.
- `required_slots`: slots that must be resolved or clarified.

## Deposit Metrics

| metric_id | business_line | grain | snapshot_type | formula | required_slots |
| --- | --- | --- | --- | --- | --- |
| deposit_balance | all | account_day | month_end_snapshot by default | Sum account balance at snapshot date | business_line if non-consolidated reporting is required; time_range |
| corporate_deposit_balance | corporate | corporate_account_day | month_end_snapshot by default | Sum corporate deposit account balance at snapshot date | time_range |
| retail_deposit_balance | retail | retail_account_day | month_end_snapshot by default | Sum retail savings/deposit account balance at snapshot date | time_range |
| avg_daily_deposit_balance | all | account_day | period_average | Average daily balance across days in period | business_line if ambiguous; time_range |
| deposit_growth_amount | all | account_day | point_to_point_change | Current snapshot balance minus base snapshot balance | business_line if ambiguous; current_period; base_period |

Rules:

- Treat "余额", "规模", "时点" as snapshot metrics unless the utterance says "日均", "平均", or local metric metadata overrides it.
- Treat month-only queries as month-end snapshot for balance metrics.
- Ask whether the user wants 对公, 个人, 普惠, or 全行汇总 when business line changes the metric table or product scope.

## Loan Metrics

| metric_id | business_line | grain | snapshot_type | formula | required_slots |
| --- | --- | --- | --- | --- | --- |
| loan_balance | all | loan_contract_day | month_end_snapshot by default | Sum outstanding principal balance at snapshot date | business_line if ambiguous; time_range |
| corporate_loan_balance | corporate | corporate_loan_contract_day | month_end_snapshot by default | Sum outstanding principal for corporate loan contracts | time_range |
| retail_loan_balance | retail | retail_loan_contract_day | month_end_snapshot by default | Sum outstanding principal for retail loan contracts | time_range |
| inclusive_loan_balance | inclusive_finance | loan_contract_day | month_end_snapshot by default | Sum outstanding principal for inclusive-finance eligible loans | time_range; inclusive_scope if local rules vary |
| loan_disbursement_amount | all | loan_disbursement_transaction | period_sum | Sum loan disbursement amount during period | business_line if ambiguous; time_range |
| corporate_loan_disbursement_amount | corporate | loan_disbursement_transaction | period_sum | Sum corporate loan disbursement amount during period | time_range |
| retail_loan_disbursement_amount | retail | loan_disbursement_transaction | period_sum | Sum retail loan disbursement amount during period | time_range |

Rules:

- "投放", "发放", "放款" are period-sum metrics, not end-of-period balances.
- "贷款余额" and "信贷余额" are outstanding balance metrics.
- "普惠" must follow local eligibility rules. Ask if eligibility is not defined.

## Risk Metrics

| metric_id | business_line | grain | snapshot_type | formula | required_slots |
| --- | --- | --- | --- | --- | --- |
| overdue_loan_balance | all | loan_contract_day | month_end_snapshot by default | Sum overdue principal balance at snapshot date | business_line if ambiguous; time_range; overdue_rule if local rules vary |
| npl_balance | all | loan_contract_day | month_end_snapshot by default | Sum outstanding principal where five-category classification is substandard, doubtful, or loss | business_line if ambiguous; time_range |
| npl_ratio | all | loan_contract_day | month_end_snapshot by default | npl_balance / loan_balance | business_line if ambiguous; time_range; numerator; denominator |

Rules:

- For 不良贷款率, set `formula` to `npl_balance / loan_balance` and include numerator and denominator notes in `sql_readiness.notes` if no schema mapping exists.
- Ask for business line when "不良率" could refer to corporate, retail, inclusive finance, or whole-bank loan book.

## Customer Metrics

| metric_id | business_line | grain | snapshot_type | formula | required_slots |
| --- | --- | --- | --- | --- | --- |
| customer_count | all | customer | snapshot_distinct_count | Count distinct valid customers in scope | business_line if ambiguous; time_range |
| corporate_customer_count | corporate | corporate_customer | snapshot_distinct_count | Count distinct corporate customers in valid relationship status | time_range; customer_status if local rules vary |
| retail_customer_count | retail | retail_customer | snapshot_distinct_count | Count distinct retail customers in valid relationship status | time_range; customer_status if local rules vary |
| new_customer_count | all | customer_event | period_distinct_count | Count customers whose qualifying new-customer event occurs during period | business_line if ambiguous; time_range; new_customer_event |
| new_corporate_customer_count | corporate | corporate_customer_event | period_distinct_count | Count corporate customers newly opened or established during period | time_range; new_customer_event |
| new_retail_customer_count | retail | retail_customer_event | period_distinct_count | Count retail customers newly opened or established during period | time_range; new_customer_event |
| active_customer_count | all | customer_activity | period_distinct_count | Count distinct customers satisfying active rule during period | business_line if ambiguous; time_range; active_rule |

Rules:

- "客户数" needs business-line clarification unless the user says 全行/全部客户 and schema supports consolidated customer identity.
- "新增客户" requires an event definition. If local rules are absent, ask whether it means 开户, 建档, 首次交易, or 首次达标.
- "活跃客户" requires an active rule. Ask unless a project-specific rule is available.

## Channel, Card, Wealth, And Income Metrics

| metric_id | business_line | grain | snapshot_type | formula | required_slots |
| --- | --- | --- | --- | --- | --- |
| mobile_active_user_count | retail | user_activity | period_distinct_count | Count distinct mobile banking users satisfying active rule during period | time_range; active_rule |
| card_issued_count | retail | card_event | period_count | Count issued cards during period | time_range; card_type if ambiguous |
| aum_balance | retail | customer_day | month_end_snapshot by default | Sum retail customer financial assets at snapshot date | time_range; customer_segment optional |
| wealth_product_sales | retail | transaction | period_sum | Sum wealth product purchase or sales amount during period | time_range; product_scope if ambiguous |
| transaction_amount | all | transaction | period_sum | Sum transaction amount during period | business_line or channel if ambiguous; time_range |
| transaction_count | all | transaction | period_count | Count transactions during period | business_line or channel if ambiguous; time_range |
| fee_income | all | accounting_entry | period_sum | Sum fee and commission income during period | business_line if ambiguous; time_range |
| interest_income | all | accounting_entry | period_sum | Sum interest income during period | business_line if ambiguous; time_range |

Rules:

- 手机银行活跃用户 usually belongs to retail unless a corporate mobile banking product is explicitly named.
- AUM and wealth product sales usually belong to retail/private banking.
- Income metrics may need accounting subject scope. Ask if the user asks for 中收/息收 without business line or product scope.
