# Dashboard Layout Rules

Use a 12-column grid by default. Use stable widget sizes to avoid layout jumping when data changes.

## Grid Sizes

| widget kind | desktop size | tablet size | mobile size |
| --- | --- | --- | --- |
| KPI card | 3 cols x 2 rows | 6 cols x 2 rows | 12 cols x 2 rows |
| Primary trend/comparison | 8 cols x 5 rows | 12 cols x 5 rows | 12 cols x 5 rows |
| Secondary chart | 4 or 6 cols x 5 rows | 12 cols x 5 rows | 12 cols x 5 rows |
| Ranking chart | 6 cols x 5 rows | 12 cols x 5 rows | 12 cols x 5 rows |
| Composition chart | 4 or 6 cols x 5 rows | 12 cols x 5 rows | 12 cols x 5 rows |
| Detail table | 12 cols x 6 rows | 12 cols x 6 rows | 12 cols x 6 rows |

## Section Patterns

### Overview

1. KPI strip.
2. Main trend chart.
3. Breakdown section with 2 charts.
4. Ranking or detail section.

### Risk Analysis

1. KPI strip: loan balance, NPL balance, NPL ratio, overdue balance.
2. NPL ratio trend.
3. Risk classification composition.
4. Branch or product risk ranking.
5. Detail table of high-risk customers/contracts.

### Performance

1. KPI strip for total and growth.
2. Main ranking chart.
3. Trend or comparison chart.
4. Detail table.

### Customer Analysis

1. Customer KPIs.
2. Customer trend.
3. Segment or channel composition.
4. Branch/customer manager ranking.
5. Customer detail table if available.

## Widget Priority

Assign priority from 1 to 5:

- 1: KPI cards and primary chart.
- 2: primary breakdown and ranking.
- 3: secondary charts.
- 4: detail tables.
- 5: optional explanatory or fallback widgets.

## Layout Rules

- Put 3 to 5 KPI cards in the first row when available.
- Use one large primary chart per dashboard section. Avoid making every chart the same size.
- Put related charts in the same section.
- Put filters above the first section, not inside individual cards, unless the filter is widget-specific.
- Keep tables full width when they contain many columns.
- If chart count exceeds 8, group lower-priority charts into tabs or collapsible sections.
- If there is no trend chart, use the highest-confidence ranking or comparison chart as the primary chart.
