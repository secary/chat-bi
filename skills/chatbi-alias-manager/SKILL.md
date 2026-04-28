---
name: chatbi-alias-manager
description: Use when Codex or another agent needs to add missing Chinese synonyms, aliases, or business phrasing to the local ChatBI semantic layer, especially when a natural-language query uses a new word that should map to an existing metric or dimension in alias_mapping. Supports safely inserting aliases for governed metrics and dimensions such as 销售额, 毛利, 目标完成率, 客户留存率, 区域, 时间, 部门, 产品类别, 产品名称, 渠道, and 客户类型.
---

# ChatBI Alias Manager

Use this skill to add missing natural-language synonyms to the ChatBI semantic layer.

## Workflow

1. Identify the new word the user used, such as `成交方式`.
2. Map it to an existing standard metric or dimension, such as `渠道`.
3. Use `scripts/add_alias_mapping.py` to validate and insert the alias into `alias_mapping`.
4. Run the original query again with `chatbi-semantic-query` if the user wants verification.
5. When the alias should survive database rebuilds, also add the printed values tuple to `init.sql` under the `INSERT INTO alias_mapping` block.

## Commands

```bash
python3 scripts/add_alias_mapping.py --alias "成交方式" --standard "渠道" --type "维度" --print-init-sql
python3 scripts/add_alias_mapping.py --alias "业务条线" --standard "产品类别" --type "维度" --print-init-sql
python3 scripts/add_alias_mapping.py --alias "营收" --standard "销售额" --type "指标" --print-init-sql
```

Run commands from this skill directory, or pass the full path to the bundled script.

## Standard Names

Prefer these current standard names:

- 指标: `销售额`, `订单数`, `客户数`, `毛利`, `毛利率`, `目标完成率`, `新增客户数`, `客户留存率`
- 维度: `时间`, `月份`, `区域`, `部门`, `产品类别`, `产品名称`, `渠道`, `客户类型`

Use an existing standard name. Do not create a new metric or dimension with this skill.

## Presentation Guidance

This skill changes semantic metadata, so its own output should be a concise text status rather than a chart.

- Return a text confirmation for inserted or existing aliases, such as `成交方式 -> 渠道 (维度)`.
- If `--print-init-sql` is used, show the generated values tuple as a code block or developer detail.
- Do not generate bar, line, pie, or KPI charts from alias insertion results.
- If the user asks to verify the original data question after adding an alias, run or delegate to `chatbi-semantic-query`; that follow-up query may produce charts using its Visualization Guidance.

## Database Defaults

The bundled script defaults to:

- Host: `127.0.0.1`
- Port: `3307`
- Database: `chatbi_demo`
- User: `demo_user`
- Password: `demo_pass`

Override with environment variables:

- `CHATBI_DB_HOST`
- `CHATBI_DB_PORT`
- `CHATBI_DB_USER`
- `CHATBI_DB_PASSWORD`
- `CHATBI_DB_NAME`

## Safety

Only insert rows into `alias_mapping`. Do not update or delete existing aliases unless the user explicitly asks. Validate the standard name before insertion. If the database is running in Docker and local MySQL access is blocked by the sandbox, request permission to run the script with elevated local network access.
