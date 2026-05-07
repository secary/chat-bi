import type {
  CustomerByRegionRow,
  SalesByMonthRow,
  SalesByRegionRow,
} from '../types/dashboard';

export function buildRegionPieOption(rows: SalesByRegionRow[]): Record<string, unknown> {
  const data = rows.map((r) => ({
    name: r.region,
    value: r.sales_amount,
  }));
  return {
    tooltip: { trigger: 'item', formatter: '{b}: {c} 元 ({d}%)' },
    legend: { type: 'scroll', orient: 'vertical', left: 'left', top: 'middle' },
    series: [
      {
        type: 'pie',
        radius: ['35%', '65%'],
        center: ['58%', '50%'],
        data,
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.2)',
          },
        },
      },
    ],
  };
}

export function buildMonthlyBarOption(rows: SalesByMonthRow[]): Record<string, unknown> {
  const categories = rows.map((r) => r.month);
  const values = rows.map((r) => r.sales_amount);
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 48, right: 24, top: 24, bottom: 48 },
    xAxis: {
      type: 'category',
      data: categories,
      axisLabel: { rotate: rows.length > 6 ? 30 : 0 },
    },
    yAxis: { type: 'value', name: '销售额（元）' },
    series: [
      {
        type: 'bar',
        data: values,
        itemStyle: { color: '#3b82f6' },
      },
    ],
  };
}

export function buildCustomerBarOption(rows: CustomerByRegionRow[]): Record<string, unknown> {
  const categories = rows.map((r) => r.region);
  const values = rows.map((r) => r.active_customers);
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 48, right: 24, top: 24, bottom: 48 },
    xAxis: { type: 'category', data: categories },
    yAxis: { type: 'value', name: '活跃客户（人）' },
    series: [
      {
        type: 'bar',
        data: values,
        itemStyle: { color: '#10b981' },
      },
    ],
  };
}
