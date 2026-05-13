---
name: chatbi-file-ingestion
description: Use when Codex or another agent needs to read a user-uploaded CSV or Excel file for ChatBI, validate whether it matches the existing sales_order or customer_profile schema, directly analyze matched business tables, and fall back to pandas-based generic analysis when the uploaded structure does not fit the governed tables.
---

# ChatBI File Ingestion

Use this skill when the user wants ChatBI to read their own uploaded CSV or Excel data file.

## Workflow

1. Ask the application or caller for the local uploaded file path, then pass that path to `scripts/inspect_uploaded_table.py`.
2. Let the script infer the target table from headers, or pass `--table sales_order` / `--table customer_profile` when the user specified the table.
3. The script always validates headers and basic value types first.
4. If the file fully matches `sales_order` or `customer_profile`, the skill returns `analysis_mode = schema_direct` and emits deterministic business analysis based on the governed table schema.
5. If the file does not fully match those tables, the skill returns `analysis_mode = pandas_fallback` and emits a pandas-based generic profile: shape, dtypes, null counts, numeric summary, categorical top values, and preview rows.
6. Use `--json` for agent or UI integration. If downstream analysis or charting needs full row data, rerun with `--include-rows`.

## Commands

```bash
python3 scripts/inspect_uploaded_table.py /path/to/upload.csv --json
python3 scripts/inspect_uploaded_table.py /path/to/upload.xlsx --table sales_order --json
python3 scripts/inspect_uploaded_table.py /path/to/upload.csv --json --include-rows
python3 scripts/inspect_uploaded_table.py /path/to/customer.xlsx --table customer_profile --sample-size 10
```

Run commands from this skill directory, or pass the full path to the bundled script.

## Supported Tables

The initial schema mirrors the current database tables:

- `sales_order`: `order_date`, `region`, `department`, `product_category`, `product_name`, `channel`, `customer_type`, `sales_amount`, `order_count`, `customer_count`, `gross_profit`, `target_amount`
- `customer_profile`: `stat_month`, `region`, `customer_type`, `new_customers`, `active_customers`, `retained_customers`, `churned_customers`

Headers may use database field names or the current Chinese business names, such as `订单日期`, `区域`, `销售额`, `月份`, `活跃客户数`.

## Presentation Guidance

This skill should first explain whether the upload matched a governed business table.

- `schema_direct`: summarize business metrics and highlights from the uploaded rows using the matched table semantics.
- `pandas_fallback`: summarize the uploaded file as a general-purpose table without pretending it is one of the governed business tables.

Return a small preview table in both modes. Do not create business charts from unimported uploaded data unless the user explicitly asks for exploratory preview charts.

## Safety

This skill only reads local CSV/XLSX files and validates them. It must not write to MySQL or modify semantic metadata. Treat user-uploaded data as untrusted: report validation issues, keep previews small, and avoid printing full files.
