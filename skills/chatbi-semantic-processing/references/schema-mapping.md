# Schema Mapping Starter

Use this file only when the repository does not provide richer schema metadata. Treat mappings as candidates, not guaranteed physical schema.

## Mapping Output Shape

When adding schema hints to Query Intent JSON, use objects like:

```json
{
  "canonical_id": "corporate_deposit_balance",
  "type": "metric",
  "candidate_tables": ["fact_corporate_deposit_daily"],
  "candidate_columns": ["balance_amt"],
  "join_keys": ["org_id", "customer_id", "account_id", "stat_date"],
  "notes": ["Use month-end stat_date for balance query."]
}
```

## Metric Candidates

| metric_id | candidate_tables | candidate_columns | date_column | notes |
| --- | --- | --- | --- | --- |
| deposit_balance | fact_deposit_daily | balance_amt | stat_date | Consolidated deposit snapshot if available. |
| corporate_deposit_balance | fact_corporate_deposit_daily | balance_amt | stat_date | Filter or table should already represent corporate business. |
| retail_deposit_balance | fact_retail_deposit_daily | balance_amt | stat_date | Retail savings/deposit balances. |
| avg_daily_deposit_balance | fact_deposit_daily | balance_amt | stat_date | Average daily rows across period before aggregation if needed. |
| loan_balance | fact_loan_daily | loan_balance_amt, principal_balance_amt | stat_date | Consolidated outstanding loan balance. |
| corporate_loan_balance | fact_corporate_loan_daily | principal_balance_amt | stat_date | Corporate outstanding principal. |
| retail_loan_balance | fact_retail_loan_daily | principal_balance_amt | stat_date | Retail outstanding principal. |
| inclusive_loan_balance | fact_inclusive_loan_daily | principal_balance_amt | stat_date | Requires inclusive-finance eligibility flag if no dedicated table exists. |
| loan_disbursement_amount | fact_loan_disbursement | disbursement_amt | disbursement_date | Period-sum transaction/event table. |
| corporate_loan_disbursement_amount | fact_corporate_loan_disbursement | disbursement_amt | disbursement_date | Corporate disbursement event table. |
| retail_loan_disbursement_amount | fact_retail_loan_disbursement | disbursement_amt | disbursement_date | Retail disbursement event table. |
| overdue_loan_balance | fact_loan_daily | overdue_principal_amt | stat_date | Confirm overdue definition if absent. |
| npl_balance | fact_loan_daily | principal_balance_amt | stat_date | Filter five_category in substandard/doubtful/loss. |
| npl_ratio | fact_loan_daily | principal_balance_amt, five_category | stat_date | Formula: NPL principal / total loan principal. |
| customer_count | dim_customer, fact_customer_snapshot | customer_id | stat_date | Use snapshot table if available. |
| corporate_customer_count | dim_corporate_customer, fact_corporate_customer_snapshot | customer_id | stat_date | Corporate customer identity may differ from retail identity. |
| retail_customer_count | dim_retail_customer, fact_retail_customer_snapshot | customer_id | stat_date | Retail customer identity. |
| new_customer_count | fact_customer_event | customer_id | event_date | Filter qualifying new-customer event. |
| active_customer_count | fact_customer_activity | customer_id | activity_date | Requires active rule. |
| mobile_active_user_count | fact_mobile_banking_activity | user_id, customer_id | activity_date | Requires active rule such as login or transaction. |
| card_issued_count | fact_card_opening | card_id | issue_date | Retail card issuance. |
| transaction_amount | fact_transaction | transaction_amt | transaction_date | Filter channel/product/business line if provided. |
| transaction_count | fact_transaction | transaction_id | transaction_date | Count transaction rows or distinct transaction_id. |
| aum_balance | fact_retail_aum_daily | aum_amt | stat_date | Retail/wealth customer asset snapshot. |
| wealth_product_sales | fact_wealth_transaction | purchase_amt, sales_amt | transaction_date | Confirm purchase vs sales amount if ambiguous. |
| fee_income | fact_income_accounting | fee_income_amt | accounting_date | May require subject code mapping. |
| interest_income | fact_income_accounting | interest_income_amt | accounting_date | May require product or subject code mapping. |

## Dimension Candidates

| dimension_id | candidate_tables | candidate_columns | join_keys | notes |
| --- | --- | --- | --- | --- |
| business_line | dim_business_line | business_line_code, business_line_name | business_line_code | Prefer canonical values from SKILL.md. |
| branch | dim_org | branch_id, branch_name, org_id, org_name | org_id | Branch may mean managing branch, opening branch, or transaction branch. Clarify if material. |
| region | dim_region, dim_org | region_code, province_code, city_code | region_code, org_id | Often derived from organization hierarchy. |
| customer_type | dim_customer | customer_type_code, customer_type_name | customer_id | Do not use as replacement for business_line when metric has separate corporate/retail tables. |
| customer_segment | dim_customer_segment | segment_code, segment_name | customer_id | Retail tier or corporate segmentation may use different tables. |
| product | dim_product | product_code, product_name | product_code | Product hierarchy may be required. |
| account_type | dim_account | account_type_code, account_type_name | account_id | Mostly deposit/account facts. |
| loan_type | dim_loan_product | loan_type_code, loan_type_name | loan_type_code | Loan product or loan purpose. |
| deposit_type | dim_deposit_product | deposit_type_code, deposit_type_name | deposit_type_code | Current, fixed, notice, agreement deposit, etc. |
| channel | dim_channel | channel_code, channel_name | channel_code | Transaction or event facts. |
| currency | dim_currency | currency_code | currency_code | Default CNY only when local rules allow. |
| risk_level | dim_risk_classification | risk_level_code, five_category | risk_level_code | Loan risk and customer risk are different. |
| employee | dim_employee | employee_id, employee_name | employee_id | Customer manager, account manager, or handler may differ. |
| industry | dim_industry | industry_code, industry_name | industry_code | Corporate customer dimension. |
| time | dim_date | date_id, stat_date, month_id, quarter_id, year_id | stat_date | Use reporting calendar if available. |

## Join Guidance

- Use organization joins carefully: branch can mean account-opening branch, managing branch, transaction branch, or customer-owning branch.
- For customer metrics, do not join corporate and retail customer dimensions unless the repository has a consolidated customer master.
- For balance metrics, use snapshot date filters. For period-sum metrics, use event date ranges.
- For ratio metrics, calculate numerator and denominator at the same grain and period before division.
- For rankings, aggregate at the requested entity dimension first, then sort and limit.
