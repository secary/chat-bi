# Time Expression Rules

Normalize all dates to ISO strings. Use the current execution date only for relative expressions.

## Relative Periods

| expression | normalized intent |
| --- | --- |
| 今天 | current date, grain day |
| 昨天 | current date minus 1 day, grain day |
| 本周 | current natural week to date unless closed-period reporting is required |
| 上周 | previous natural week |
| 本月 | current natural month to date unless closed-period reporting is required |
| 上月 | previous natural month |
| 最近一个月 | rolling 1 month ending on current date, not previous natural month |
| 近30天 | rolling 30 days ending on current date |
| 本季 | current natural quarter to date |
| 上季 | previous natural quarter |
| 今年 | current natural year to date |
| 去年 | previous natural year |
| 年初至今 | from Jan 1 of current year to current date |

## Explicit Periods

- `2026年4月`, `2026-04`: natural month `2026-04-01` to `2026-04-30`.
- `2026年一季度`, `2026Q1`: quarter start to quarter end.
- `2025年`: natural year `2025-01-01` to `2025-12-31`.
- `4月末`, `月末`, `期末`: point-in-time period end.
- `月初`, `期初`: point-in-time period start.

## Comparison Terms

- `同比`: prior-year same period.
- `环比`: previous comparable period.
- `较年初`: compare current period end with current year start.
- `较上月末`: compare current period end with previous month end.
- `增幅`, `增长率`: `(current - comparison) / comparison`.
- `增量`, `新增`, `增长额`: `current - comparison`.

## Reporting Calendar

If the project has a banking reporting calendar, fiscal calendar, or holiday-aware data date, use it. Otherwise, use natural calendar periods and mark `calendar_type: "natural"`.

If the user asks "最新", "当前", or "截至目前", prefer the latest available data date if schema or metadata exposes one. If not available, use the current date and set `assumptions`.
