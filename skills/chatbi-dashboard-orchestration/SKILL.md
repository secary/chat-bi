---
name: dashboard-orchestration
description: Dashboard auto-orchestration for ChatBI and analytics workflows. Use when Codex needs to generate a dashboard layout and frontend-ready dashboard JSON from multiple chart recommendations, Query Intent JSON objects, SQL result summaries, or BI analysis goals, especially when turning generated charts into a coherent dashboard.
---

# Dashboard Orchestration

Use this skill after semantic parsing, SQL execution, and chart recommendation to arrange charts into a coherent dashboard.

## Workflow

1. Preserve the user question, dashboard goal, upstream Query Intent JSON, and chart specs if provided.
2. Identify dashboard intent with `references/dashboard-intent-rules.md`.
3. Group charts into sections with `references/dashboard-layout-rules.md`.
4. Assign visual priority:
   - headline KPI cards first
   - primary trend or comparison chart second
   - ranking/composition/detail charts after the primary story
5. Choose grid layout, card sizes, and responsive behavior with `references/dashboard-layout-rules.md`.
6. Add interaction contracts with `references/dashboard-interaction-rules.md`.
7. Emit frontend-ready dashboard JSON matching `references/dashboard-spec-schema.md`.
8. Include `confidence`, `decision_factors`, `warnings`, and missing inputs.

## Dashboard Principles

- Build the dashboard around the user's analysis story, not around the order of SQL queries.
- Put the most decision-relevant KPI or trend above supporting breakdowns.
- Keep banking BI dashboards dense, readable, and operational.
- Avoid decorative layout. Prefer predictable cards, aligned grids, and clear section titles.
- Do not invent charts. Use provided chart specs or explicitly mark recommended missing charts in `missing_inputs`.
- Use tables for detail and audit views, usually at the bottom.

## Banking Dashboard Defaults

- Top row: 3 to 5 KPI cards when headline metrics exist.
- Second row: main trend, comparison, or risk chart.
- Middle rows: branch/product/channel/customer segment breakdowns.
- Bottom row: detail table, exception list, or drill-down table.
- Global filters: date range, branch/org, business line, product, customer segment.
- Common interactions: cross-filter, drilldown, tooltip, export, reset filters.

## Output Contract

Always emit valid JSON following `references/dashboard-spec-schema.md`.

The dashboard spec should include:

- `dashboard_title`
- `layout`
- `global_filters`
- `sections`
- `widgets`
- `interactions`
- `responsive`
- `data_dependencies`
- `warnings`

If only one chart is available, still produce a single-chart dashboard layout with optional KPI or table placeholders only when explicitly provided by upstream inputs.

## Reference Files

- `references/dashboard-intent-rules.md`: dashboard intent types and banking scenarios.
- `references/dashboard-layout-rules.md`: grid, section, priority, and responsive layout rules.
- `references/dashboard-interaction-rules.md`: filter, drilldown, linkage, and export behavior.
- `references/dashboard-spec-schema.md`: frontend-ready dashboard JSON schema and examples.
