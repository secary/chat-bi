import { describe, expect, it } from 'vitest';
import {
  buildCustomerBarOption,
  buildMonthlyBarOption,
  buildRegionPieOption,
} from './dashboardCharts';

describe('dashboardCharts', () => {
  it('buildRegionPieOption maps regions to series data', () => {
    const opt = buildRegionPieOption([
      { region: '华东', sales_amount: 100 },
      { region: '华北', sales_amount: 50 },
    ]);
    const series = opt.series as Array<{ type: string; data: { name: string; value: number }[] }>;
    expect(series[0].type).toBe('pie');
    expect(series[0].data).toHaveLength(2);
    expect(series[0].data[0]).toEqual({ name: '华东', value: 100 });
  });

  it('buildMonthlyBarOption sets categories from months', () => {
    const opt = buildMonthlyBarOption([
      { month: '2026-01', sales_amount: 10 },
      { month: '2026-02', sales_amount: 20 },
    ]);
    const xAxis = opt.xAxis as { data: string[] };
    const series = opt.series as Array<{ type: string; data: number[] }>;
    expect(xAxis.data).toEqual(['2026-01', '2026-02']);
    expect(series[0].type).toBe('bar');
    expect(series[0].data).toEqual([10, 20]);
  });

  it('buildCustomerBarOption maps active_customers', () => {
    const opt = buildCustomerBarOption([{ region: '华东', active_customers: 99 }]);
    const series = opt.series as Array<{ data: number[] }>;
    expect(series[0].data).toEqual([99]);
  });
});
