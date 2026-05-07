# Clarification Policy

Ask follow-up questions only when the missing or ambiguous slot can materially change the SQL or metric definition.

## Required Slots

| slot | ask when missing |
| --- | --- |
| business_line | Ask when the same utterance could mean 对公业务, 个人业务, 普惠业务, or whole-bank consolidated reporting. |
| metric | Always, unless the utterance clearly implies one metric. |
| time_range | Ask if the question is time-dependent and no safe default is allowed. Otherwise apply the default latest completed natural month. |
| entity_dimension | Ask for ranking, top N, distribution, or comparison questions without a target dimension. |
| product_scope | Ask when terms like 规模, 余额, 新增, 或销量 could refer to multiple banking products. |
| customer_scope | Ask when customer metrics could mean individual, corporate, small business, active, opened, managed, or all customers. |
| active_rule | Ask when "活跃" has no project-specific definition and affects the result. |
| currency | Ask for cross-currency amount metrics if no default currency is configured. |

## Follow-Up Style

- Ask one concise question when possible.
- Provide 2 to 4 concrete options if the ambiguity is categorical.
- Do not ask for technical table or column names from a business user.
- Preserve the partially resolved intent in the JSON.

## Examples

User: `查一下存款规模`

Missing or ambiguous slots:

- `business_line`: 对公、个人、普惠或全行汇总口径都会改变指标口径。
- `time_range`: use default latest completed natural month if allowed.

Ask:

`请问要看哪个业务线的存款规模？例如对公、个人、普惠，还是全行汇总口径。`

If the user already specified the business line but local policy forbids default time, ask:

`请问要看哪个统计期的存款余额？例如上月末、本月末或指定日期。`

User: `各网点客户排名`

Ask:

`请问按哪个指标给各网点排名？例如客户数、新增客户数、AUM余额或存款余额。`

User: `贷款余额同比`

Ask:

`请问贷款余额按哪个业务线统计？例如对公贷款、个人贷款、普惠贷款，还是全行汇总口径。`
