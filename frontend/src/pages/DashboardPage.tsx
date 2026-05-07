import { useEffect, useMemo, useState } from 'react';
import { getDashboardOverview } from '../api/client';
import { ChartRenderer } from '../components/ChartRenderer';
import { KPICards } from '../components/KPICards';
import type { DashboardOverview } from '../types/dashboard';
import type { KpiCard } from '../types/message';
import {
  buildCustomerBarOption,
  buildMonthlyBarOption,
  buildRegionPieOption,
} from '../lib/dashboardCharts';
import { logger } from '../lib/logger';

const moneyFmt = new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 0 });

export function DashboardPage() {
  const [data, setData] = useState<DashboardOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      setLoading(true);
      setError(null);
      try {
        const overview = await getDashboardOverview();
        if (!cancelled) setData(overview);
      } catch (e) {
        logger.error('dashboard overview', e);
        if (!cancelled) setError(e instanceof Error ? e.message : '加载失败');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const kpiCards: KpiCard[] = useMemo(() => {
    if (!data) return [];
    const { kpis } = data;
    const range =
      kpis.min_date && kpis.max_date ? `${kpis.min_date} ~ ${kpis.max_date}` : '—';
    return [
      {
        label: '销售总额',
        value: moneyFmt.format(kpis.total_sales),
        unit: '元',
        status: 'success',
      },
      {
        label: '订单明细条数',
        value: String(kpis.row_count),
        unit: '条',
        status: 'neutral',
      },
      {
        label: '数据时间范围',
        value: range,
        unit: '',
        status: 'neutral',
      },
      {
        label: '覆盖区域数',
        value: String(kpis.region_count),
        unit: '个',
        status: 'neutral',
      },
    ];
  }, [data]);

  const pieOpt = data ? buildRegionPieOption(data.sales_by_region) : {};
  const barMonthOpt = data ? buildMonthlyBarOption(data.sales_by_month) : {};
  const barCustOpt = data ? buildCustomerBarOption(data.customer_by_region) : {};

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center bg-gray-50 text-sm text-gray-500">
        加载仪表盘…
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 bg-gray-50 p-6">
        <p className="text-sm text-red-600">{error}</p>
      </div>
    );
  }

  if (!data) {
    return null;
  }

  const semanticEntries = Object.entries(data.semantic_counts).sort((a, b) =>
    a[0].localeCompare(b[0]),
  );

  return (
    <div className="h-full overflow-y-auto bg-gray-50 p-6">
      <div className="mx-auto max-w-6xl space-y-6">
        <header>
          <h2 className="text-lg font-semibold text-gray-900">数据仪表盘</h2>
          <p className="mt-1 text-sm text-gray-500">
            当前业务库中的订单与客户概况，以及语义层资产规模
          </p>
        </header>

        {data.warnings.length > 0 && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
            <ul className="list-inside list-disc space-y-1">
              {data.warnings.map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          </div>
        )}

        <KPICards cards={kpiCards} />

        <div className="grid gap-6 lg:grid-cols-2">
          <div>
            <h3 className="mb-2 text-sm font-medium text-gray-700">销售额占比（按区域）</h3>
            <ChartRenderer option={pieOpt} />
          </div>
          <div>
            <h3 className="mb-2 text-sm font-medium text-gray-700">销售额趋势（按月）</h3>
            <ChartRenderer option={barMonthOpt} />
          </div>
        </div>

        <div>
          <h3 className="mb-2 text-sm font-medium text-gray-700">活跃客户（按区域汇总）</h3>
          <ChartRenderer option={barCustOpt} />
        </div>

        <section className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
          <h3 className="text-sm font-medium text-gray-900">语义层与数据目录</h3>
          <p className="mt-1 text-xs text-gray-500">各元数据表当前行数（表不存在时为 0）</p>
          <dl className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {semanticEntries.map(([name, count]) => (
              <div
                key={name}
                className="flex items-center justify-between rounded-md border border-gray-100 bg-gray-50 px-3 py-2"
              >
                <dt className="font-mono text-xs text-gray-600">{name}</dt>
                <dd className="text-sm font-semibold text-gray-900">{count}</dd>
              </div>
            ))}
          </dl>
        </section>
      </div>
    </div>
  );
}
