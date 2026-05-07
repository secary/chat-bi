---
name: chatbi-semantic-processing
description: Banking ChatBI semantic processing for intelligent BI questions. Use when Codex needs to normalize ambiguous Chinese or bilingual banking business questions into a standard Query Intent JSON by resolving metric synonyms, dimension synonyms, time expressions, missing slots, ambiguity, and downstream Text-to-SQL readiness.
---

# ChatBI Semantic Processing

Use this skill to convert a user's banking BI question into a normalized, auditable Query Intent JSON before Text-to-SQL.

## Workflow

1. Preserve the original utterance.
2. Identify the business line first: `corporate`, `retail`, `inclusive_finance`, `financial_markets`, or `unknown`.
3. Identify the business domain, such as deposit, loan, customer, card, channel, branch, risk, wealth, transaction, or marketing.
4. Resolve metric synonyms with `references/banking-semantic-catalog.md`.
5. Resolve metric definitions, calculation grain, and snapshot rules with `references/business-metric-definitions.md`.
6. Resolve dimension synonyms with `references/banking-semantic-catalog.md`.
7. Parse time expressions with `references/time-expression-rules.md`.
8. Detect filters, grouping, sorting, comparison, limit, and aggregation intent.
9. Check required slots with `references/clarification-policy.md`.
10. Add schema hints from `references/schema-mapping.md` when no richer project schema is available.
11. Return either:
   - `status: "ready"` with complete Query Intent JSON, or
   - `status: "need_clarification"` with concise follow-up questions.
12. Keep the output SQL-ready, but do not generate SQL unless explicitly asked.

## Output Contract

Always emit valid JSON matching `references/query-intent-schema.md`.

Use canonical IDs, not user-facing synonyms, in normalized fields:

- Metrics: `metric_id`
- Dimensions: `dimension_id`
- Business line: `corporate`, `retail`, `inclusive_finance`, `financial_markets`, or `unknown`
- Time grain: `day`, `week`, `month`, `quarter`, `year`, or `custom_range`
- Operators: `=`, `!=`, `>`, `>=`, `<`, `<=`, `in`, `not_in`, `between`, `like`

When uncertain, include alternatives in `ambiguities` and ask a follow-up instead of guessing if the choice changes the business meaning.

## Banking Defaults

Use these defaults only when the user does not specify and they are consistent with local business rules:

- Default time range: latest completed natural month.
- Default institution scope: whole bank.
- Default currency: CNY.
- Default aggregation: sum for balance/amount metrics, count for customer/account counts, ratio formula for rate metrics.

Do not assume retail vs corporate banking when the metric exists in both domains. Ask a clarification question because product scope, customer ID, account relationship, owner dimension, and metric definition may differ.

## Business Line Rules

Treat business line as a first-class slot, not just a filter:

- `corporate`: 对公, 公司, 企业, 单位, 机构客户, 小微企业, 对公账户, 对公存款, 对公贷款.
- `retail`: 个人, 零售, 私人客户, 储蓄客户, 借记卡, 信用卡, 手机银行个人用户, 个人贷款.
- `inclusive_finance`: 普惠, 小微, 个体工商户, 涉农, 普惠贷款. Use only when the utterance clearly points to inclusive finance; otherwise clarify whether it belongs to corporate or retail reporting.
- `financial_markets`: 同业, 金融市场, 票据, 债券, 资金业务.

When the utterance says only "客户", "存款", "贷款", "余额", "规模", "新增", or "排名" and both corporate and retail interpretations are plausible, set `business_line: "unknown"`, add `business_line` to `missing_slots`, and ask one business-line clarification question.

## Text-to-SQL Readiness

For downstream Text-to-SQL, ensure the intent contains:

- One or more canonical metrics.
- A resolved business line, unless the query is explicitly whole-bank and the downstream schema supports consolidated reporting.
- Metric definition, grain, and snapshot or period-sum semantics when relevant.
- All required dimensions or explicit no-grouping intent.
- A resolved time range and optional time grain.
- Filters separated from dimensions.
- Comparison periods represented explicitly.
- Missing slots represented in `missing_slots`.

If schema metadata is available in the current repository, map canonical metric and dimension IDs to table and column candidates in `sql_readiness.schema_hints`. If no schema is available, leave `schema_hints` empty and keep the intent business-level.

Prefer repository schema metadata over bundled schema hints. Use `references/schema-mapping.md` only as a starter mapping or when the project has no live schema documentation.

## Reference Files

- `references/banking-semantic-catalog.md`: banking metric and dimension synonym catalog.
- `references/business-metric-definitions.md`: business definitions, formulas, grains, and snapshot rules.
- `references/time-expression-rules.md`: Chinese time-expression parsing rules.
- `references/clarification-policy.md`: missing-slot and ambiguity follow-up policy.
- `references/query-intent-schema.md`: standard Query Intent JSON schema and examples.
- `references/schema-mapping.md`: starter mapping from canonical intent fields to likely table and column candidates.
