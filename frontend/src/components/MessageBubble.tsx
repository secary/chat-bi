import ReactECharts from 'echarts-for-react';
import type { ChatMessage } from '../types/message';
import { ThinkingBubble } from './ThinkingBubble';
import { ChartRenderer } from './ChartRenderer';
import { KPICards } from './KPICards';
import { tokenizeInlineMarkdown } from '../lib/inlineMarkdown';
import { parseMarkdownBlocks } from '../lib/markdownBlocks';

interface MessageBubbleProps {
  message: ChatMessage;
}

function formatAxisNumber(value: unknown): string {
  const num = typeof value === 'number' ? value : Number(value);
  if (!Number.isFinite(num)) return String(value ?? '');
  const abs = Math.abs(num);
  if (abs >= 1e8) {
    return `${trimZero((num / 1e8).toFixed(1))}亿`;
  }
  if (abs >= 1e4) {
    return `${trimZero((num / 1e4).toFixed(1))}万`;
  }
  return trimZero(num.toFixed(abs >= 100 ? 0 : 1));
}

function trimZero(value: string): string {
  return value.replace(/\.0+$/, '').replace(/(\.\d*[1-9])0+$/, '$1');
}

function wrapCategoryLabel(value: unknown): string {
  const text = String(value ?? '').trim();
  if (!text) return '';
  if (text.length <= 4) return text;
  const parts: string[] = [];
  for (let index = 0; index < text.length; index += 4) {
    parts.push(text.slice(index, index + 4));
  }
  return parts.slice(0, 2).join('\n');
}

function withDashboardTheme(option: Record<string, unknown>): Record<string, unknown> {
  const next = structuredClone(option);
  const palette = ['#0ea5e9', '#22c55e', '#8b5cf6', '#f59e0b', '#f43f5e', '#14b8a6'];

  next.backgroundColor = 'transparent';
  next.textStyle = { color: '#334155' };
  next.color = Array.isArray(next.color) && next.color.length > 0 ? next.color : palette;

  const tooltip = (next.tooltip ?? {}) as Record<string, unknown>;
  next.tooltip = {
    ...tooltip,
    backgroundColor: 'rgba(255, 255, 255, 0.98)',
    borderColor: 'rgba(148, 163, 184, 0.24)',
    borderWidth: 1,
    textStyle: { color: '#334155' },
  };

  const legend = (next.legend ?? {}) as Record<string, unknown>;
  const legendText = (legend.textStyle ?? {}) as Record<string, unknown>;
  next.legend = {
    ...legend,
    textStyle: { color: '#64748b', ...legendText },
    itemWidth: 12,
    itemHeight: 8,
    padding: Array.isArray(legend.padding) ? legend.padding : [10, 12, 14, 12],
  };

  const grid = (next.grid ?? {}) as Record<string, unknown>;
  const rawBottom = grid.bottom;
  let bottomOut: number | string = 56;
  if (typeof rawBottom === 'number' && !Number.isNaN(rawBottom)) {
    bottomOut = Math.max(56, rawBottom);
  } else if (rawBottom !== undefined && rawBottom !== null && rawBottom !== '') {
    bottomOut = rawBottom as string | number;
  }
  next.grid = {
    ...grid,
    left: 48,
    right: 24,
    top: 36,
    bottom: bottomOut,
    containLabel: grid.containLabel !== undefined ? grid.containLabel : true,
  };

  const xAxisRaw = next.xAxis;
  const xAxes = Array.isArray(xAxisRaw) ? xAxisRaw : xAxisRaw ? [xAxisRaw] : [];
  next.xAxis = xAxes.map((axis) => ({
    ...(axis as Record<string, unknown>),
    axisLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.22)' } },
    axisTick: { show: false },
    axisLabel: {
      color: '#64748b',
      margin: 14,
      rotate: 0,
      interval: 0,
      formatter: wrapCategoryLabel,
      ...(((axis as Record<string, unknown>).axisLabel as Record<string, unknown>) ?? {}),
    },
    splitLine: { show: false },
  }));

  const yAxisRaw = next.yAxis;
  const yAxes = Array.isArray(yAxisRaw) ? yAxisRaw : yAxisRaw ? [yAxisRaw] : [];
  next.yAxis = yAxes.map((axis) => ({
    ...(axis as Record<string, unknown>),
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: {
      color: '#64748b',
      margin: 10,
      formatter: formatAxisNumber,
      ...(((axis as Record<string, unknown>).axisLabel as Record<string, unknown>) ?? {}),
    },
    splitLine: {
      lineStyle: { color: 'rgba(148, 163, 184, 0.16)' },
      ...(((axis as Record<string, unknown>).splitLine as Record<string, unknown>) ?? {}),
    },
  }));

  const seriesRaw = Array.isArray(next.series) ? next.series : [];
  next.series = seriesRaw.map((item, index) => {
    const series = item as Record<string, unknown>;
    const color = palette[index % palette.length];
    const isSingleSeriesBar = series.type === 'bar' && seriesRaw.length === 1;
    if (series.type === 'line') {
      return {
        ...series,
        smooth: true,
        symbol: 'circle',
        symbolSize: 8,
        lineStyle: { width: 3, color, ...(series.lineStyle as Record<string, unknown> | undefined) },
        itemStyle: { color, borderColor: '#ffffff', borderWidth: 2, ...(series.itemStyle as Record<string, unknown> | undefined) },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: `${color}66` },
              { offset: 1, color: `${color}05` },
            ],
          },
        },
      };
    }
    if (series.type === 'bar') {
      return {
        ...series,
        barMaxWidth: 26,
        label: {
          show: true,
          position: 'top',
          color: '#64748b',
          fontSize: 11,
          formatter: ({ value }: { value: unknown }) => formatAxisNumber(value),
          ...(series.label as Record<string, unknown> | undefined),
        },
        itemStyle: {
          color: isSingleSeriesBar
            ? ({ dataIndex }: { dataIndex: number }) => palette[dataIndex % palette.length]
            : color,
          borderRadius: [8, 8, 0, 0],
          shadowBlur: 14,
          shadowColor: `${color}44`,
          ...(series.itemStyle as Record<string, unknown> | undefined),
        },
      };
    }
    if (series.type === 'pie') {
      const lbl = (series.label ?? {}) as Record<string, unknown>;
      const lblLine = (series.labelLine ?? {}) as Record<string, unknown>;
      return {
        ...series,
        center: Array.isArray(series.center) ? series.center : ['50%', '44%'],
        radius: ['26%', '42%'],
        avoidLabelOverlap: true,
        label: {
          color: '#334155',
          fontSize: 11,
          lineHeight: 15,
          ...lbl,
        },
        labelLine: {
          length: 6,
          length2: 4,
          smooth: 0.15,
          lineStyle: { color: 'rgba(148, 163, 184, 0.45)', width: 1 },
          ...lblLine,
        },
        itemStyle: { borderColor: '#ffffff', borderWidth: 2, ...(series.itemStyle as Record<string, unknown> | undefined) },
      };
    }
    return series;
  });

  return next;
}

function renderInline(content: string) {
  return tokenizeInlineMarkdown(content).map((token, idx) =>
    token.type === 'bold' ? (
      <strong key={idx} className="font-semibold text-gray-900">
        {token.value}
      </strong>
    ) : (
      <span key={idx}>{token.value}</span>
    ),
  );
}

function FormattedContent({ content }: { content: string }) {
  const blocks = parseMarkdownBlocks(content);
  return (
    <div className="space-y-1">
      {blocks.map((block, index) => {
        if (block.type === 'table') {
          return (
            <div key={index} className="my-2 overflow-x-auto rounded-lg border border-gray-200">
              <table className="min-w-full border-collapse text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    {block.header.map((cell, hIdx) => (
                      <th
                        key={hIdx}
                        className="border-b border-gray-200 px-3 py-2 text-left font-semibold text-gray-800"
                      >
                        {renderInline(cell)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {block.rows.map((row, rIdx) => (
                    <tr key={rIdx} className="border-b border-gray-100 last:border-b-0">
                      {row.map((cell, cIdx) => (
                        <td key={cIdx} className="px-3 py-2 align-top text-gray-700">
                          {renderInline(cell)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        }

        const trimmed = block.content.trim();
        if (!trimmed) {
          return <div key={index} className="h-2" />;
        }
        if (trimmed.startsWith('## ')) {
          return (
            <h2 key={index} className="pt-1 text-base font-semibold tracking-tight text-gray-950">
              {renderInline(trimmed.slice(3))}
            </h2>
          );
        }
        if (trimmed.startsWith('### ')) {
          return (
            <h3 key={index} className="pt-3 text-sm font-semibold text-gray-900">
              {renderInline(trimmed.slice(4))}
            </h3>
          );
        }
        if (/^\d+\.\s/.test(trimmed)) {
          return (
            <p key={index} className="pt-2 text-sm font-semibold text-gray-900">
              {renderInline(trimmed)}
            </p>
          );
        }
        if (/^[-•]\s+/.test(trimmed)) {
          return (
            <div key={index} className="flex gap-2 text-sm text-gray-700">
              <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-gray-400/60" />
              <span>{renderInline(trimmed.slice(2))}</span>
            </div>
          );
        }
        return (
          <p key={index} className="text-sm text-gray-700">
            {renderInline(trimmed)}
          </p>
        );
      })}
    </div>
  );
}

function AnalysisProposalCard({
  proposal,
}: {
  proposal: NonNullable<ChatMessage['analysisProposal']>;
}) {
  return (
    <div className="mt-3 rounded-xl border border-emerald-200 bg-emerald-50/60 px-4 py-3">
      <FormattedContent content={proposal.markdown} />
      <div className="mt-3 grid gap-2 md:grid-cols-2">
        {proposal.proposed_metrics.map((metric) => (
          <div key={metric.id} className="rounded-lg border border-emerald-200 bg-white px-3 py-2">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="text-sm font-semibold text-gray-950">{metric.name}</div>
                <div className="mt-1 text-xs text-gray-600">{metric.description}</div>
              </div>
              <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">
                {Math.round(metric.confidence * 100)}%
              </span>
            </div>
            <div className="mt-2 text-xs text-gray-600">{metric.formula_md}</div>
            <div className="mt-2 text-xs text-gray-500">
              ID: <span className="font-mono">{metric.id}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function kpiGridClassName(count: number): string {
  const shell =
    'grid gap-3 border-b border-slate-200/90 px-4 py-4 sm:px-5 md:px-6';
  if (count <= 1) {
    return `${shell} grid-cols-1`;
  }
  if (count === 2) {
    return `${shell} grid-cols-1 min-[480px]:grid-cols-2`;
  }
  if (count === 3) {
    return `${shell} grid-cols-1 min-[480px]:grid-cols-2 xl:grid-cols-3`;
  }
  return `${shell} grid-cols-1 min-[480px]:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4`;
}

function chartGridClassName(count: number): string {
  const shell = 'grid gap-4 border-b border-slate-200/90 px-4 py-5 sm:px-5 md:px-6';
  if (count <= 1) {
    return `${shell} grid-cols-1`;
  }
  return `${shell} grid-cols-1 min-[720px]:grid-cols-2`;
}

function DashboardMiddlewareCard({
  dashboard,
}: {
  dashboard: NonNullable<ChatMessage['dashboardReady']>;
}) {
  const kpis = dashboard.kpi_values ?? [];
  const charts = dashboard.charts ?? [];
  const tableRows = dashboard.table_rows ?? [];
  const tableCols = dashboard.table_columns ?? [];
  const kpiCount = kpis.length;
  const singleKpiHero = kpiCount === 1;
  const domainLabel = dashboard.dataset.domain_label || dashboard.dataset.domain_guess;

  return (
    <div className="mt-3 min-w-0 overflow-hidden rounded-[28px] border border-slate-200 bg-[radial-gradient(circle_at_top_left,_rgba(14,165,233,0.08),_transparent_28%),linear-gradient(180deg,_#ffffff_0%,_#f8fafc_100%)] shadow-[0_18px_50px_rgba(148,163,184,0.18)]">
      <div className="border-b border-slate-200/90 px-4 py-4 sm:px-5 md:px-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span className="inline-flex h-2.5 w-2.5 shrink-0 rounded-full bg-sky-500 shadow-[0_0_12px_rgba(14,165,233,0.35)]" />
              <span className="text-[11px] font-medium uppercase tracking-[0.32em] text-slate-500">
                Auto Analysis Board
              </span>
            </div>
            <div className="mt-2 break-words text-lg font-semibold tracking-wide text-slate-900 md:text-xl">
              {dashboard.title}
            </div>
            <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500">
              {dashboard.dataset.row_count > 0 && <span>{dashboard.dataset.row_count} 行数据</span>}
              <span>{domainLabel}</span>
              <span>已采纳 {dashboard.widgets.length} 个指标</span>
            </div>
          </div>
          <div className="flex shrink-0 flex-wrap gap-2 sm:justify-end">
            <span className="rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-[11px] font-medium text-sky-700">
              自动生成看板
            </span>
            <span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-[11px] font-medium text-slate-600">
              上传文件分析
            </span>
          </div>
        </div>
      </div>

      {kpis.length > 0 && (
        <div className={kpiGridClassName(kpiCount)}>
          {kpis.map((k, i) => (
            <div
              key={i}
              className={
                'relative flex min-h-0 min-w-0 flex-col overflow-hidden rounded-2xl border border-slate-200 bg-[linear-gradient(180deg,_rgba(255,255,255,0.96),_rgba(248,250,252,0.96))] shadow-[0_8px_30px_rgba(148,163,184,0.12)] ' +
                (singleKpiHero ? 'p-5 sm:p-6' : 'p-4 sm:p-5')
              }
            >
              <div className="pointer-events-none absolute right-0 top-0 h-24 w-24 rounded-full bg-sky-100 blur-2xl sm:h-28 sm:w-28" />
              <div className="relative z-[1] min-w-0">
                <div className="text-[11px] font-medium uppercase tracking-[0.24em] text-slate-500">
                  {k.label}
                </div>
                <div
                  className={
                    'mt-2 font-semibold tracking-tight text-slate-900 ' +
                    (singleKpiHero ? 'text-3xl sm:text-4xl' : 'text-2xl sm:text-3xl')
                  }
                >
                  {k.value}
                  {k.unit && (
                    <span className="ml-1 text-sm font-normal text-slate-500 sm:text-base">{k.unit}</span>
                  )}
                </div>
                <div className="mt-4 h-2 w-full rounded-full bg-slate-200">
                  <div
                    className="h-full rounded-full bg-[linear-gradient(90deg,_#0ea5e9,_#22c55e)] shadow-[0_0_10px_rgba(14,165,233,0.2)]"
                    style={{ width: `${Math.min(90, 42 + i * 12)}%` }}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {charts.length > 0 && (
        <div className={chartGridClassName(charts.length)}>
          {charts.map((chart, i) => {
            const opt = withDashboardTheme(chart as Record<string, unknown>);
            const w = dashboard.widgets[i];
            if (!opt?.series || (Array.isArray(opt.series) && opt.series.length === 0)) return null;
            return (
              <div
                key={i}
                className="min-w-0 rounded-[24px] border border-slate-200 bg-[linear-gradient(180deg,_#ffffff,_#f8fafc)] shadow-[0_10px_32px_rgba(148,163,184,0.14)]"
              >
                <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
                  <div>
                    <div className="text-[10px] font-medium uppercase tracking-[0.28em] text-slate-400">
                      Chart Module
                    </div>
                    <div className="mt-1 text-sm font-semibold text-slate-900">
                      {w?.title || `图表 ${i + 1}`}
                    </div>
                  </div>
                  <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[10px] text-slate-500">
                    {Array.isArray(opt.series) ? `${opt.series.length} series` : '1 series'}
                  </span>
                </div>
                <div className="px-4 pb-8 pt-2 sm:px-5">
                  <ReactECharts
                    option={opt}
                    style={{ height: 360, width: '100%' }}
                    notMerge
                    opts={{ renderer: 'canvas' }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}

      {tableRows.length > 0 && tableCols.length > 0 && (
        <div className="px-4 py-5 sm:px-5 md:px-6">
          <div className="overflow-hidden rounded-[24px] border border-slate-200 bg-[linear-gradient(180deg,_#ffffff,_#f8fafc)] shadow-[0_10px_32px_rgba(148,163,184,0.14)]">
            <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
              <div>
                <div className="text-[10px] font-medium uppercase tracking-[0.28em] text-slate-400">
                  Detail Table
                </div>
                <div className="mt-1 text-sm font-semibold text-slate-900">明细数据</div>
              </div>
              <div className="flex gap-2 text-[10px] text-slate-500">
                <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1">
                  {tableRows.length} records
                </span>
                <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1">
                  {tableCols.length} columns
                </span>
              </div>
            </div>
            <div className="max-h-80 overflow-x-auto overflow-y-auto">
              <table className="min-w-full text-sm">
                <thead className="sticky top-0 bg-slate-50/95 backdrop-blur">
                  <tr>
                    {tableCols.map((col) => (
                      <th
                        key={col}
                        className="whitespace-nowrap border-b border-slate-200 px-4 py-3 text-left text-[11px] font-medium uppercase tracking-[0.18em] text-slate-500"
                      >
                        {col}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {tableRows.slice(0, 20).map((row, i) => (
                    <tr
                      key={i}
                      className="border-b border-slate-100 transition-colors odd:bg-slate-50/50 hover:bg-sky-50"
                    >
                      {tableCols.map((col) => (
                        <td key={col} className="whitespace-nowrap px-4 py-3 text-slate-700">
                          {row[col] ?? ''}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {tableRows.length > 20 && (
              <div className="border-t border-slate-200 px-4 py-3 text-center text-xs text-slate-500">
                共 {tableRows.length} 条 · 显示前 20 条
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export function MessageBubble({ message }: MessageBubbleProps) {
  if (message.role === 'user') {
    return (
      <div className="mb-4 flex justify-end animate-fade-in">
        <div className="max-w-[80%] rounded-2xl rounded-br-sm bg-accent px-4 py-3 text-sm text-white leading-relaxed">
          {message.content}
        </div>
      </div>
    );
  }

  const isWideDashboard = Boolean(message.dashboardReady);

  return (
    <div className="mb-4 animate-fade-in">
      <div
        className={
          isWideDashboard
            ? 'w-full min-w-0 max-w-none'
            : 'max-w-[90%]'
        }
      >
        <div className="mb-1 flex items-center gap-2">
          <span className="flex h-7 w-7 items-center justify-center rounded-full bg-gray-100 text-xs font-semibold text-gray-500">
            AI
          </span>
          <span className="text-xs font-medium text-gray-500">ChatBI</span>
        </div>

        <ThinkingBubble steps={message.thinking || []} />

        {message.content && (
          <div className="prose prose-sm max-w-none rounded-2xl rounded-tl-sm bg-surface px-5 py-3.5 text-sm leading-relaxed text-gray-800 shadow-card">
            <FormattedContent content={message.content} />
          </div>
        )}

        {message.chart && <ChartRenderer option={message.chart} />}
        {message.kpiCards && <KPICards cards={message.kpiCards} />}
        {message.analysisProposal && <AnalysisProposalCard proposal={message.analysisProposal} />}
        {message.dashboardReady && <DashboardMiddlewareCard dashboard={message.dashboardReady} />}

        {message.error && (
          <div className="mt-2 rounded-xl border border-red-200 bg-red-50/80 px-4 py-3 text-sm text-red-700">
            {message.error}
          </div>
        )}
      </div>
    </div>
  );
}
