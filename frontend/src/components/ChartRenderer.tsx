import ReactECharts from 'echarts-for-react';

interface ChartRendererProps {
  option: Record<string, unknown>;
  height?: number;
  className?: string;
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

function formatCategoryLabel(value: unknown): string {
  const text = String(value ?? '').trim();
  if (!text) return '';
  const yearMonth = text.match(/^(\d{4})-(\d{2})$/);
  if (yearMonth) {
    return `${yearMonth[1]}\n${yearMonth[2]}`;
  }
  const fullDate = text.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (fullDate) {
    return `${fullDate[2]}-${fullDate[3]}\n${fullDate[1]}`;
  }
  if (/^M\d+$/i.test(text)) {
    return text.toUpperCase();
  }
  if (text.length <= 4) return text;
  const parts: string[] = [];
  for (let index = 0; index < text.length; index += 4) {
    parts.push(text.slice(index, index + 4));
  }
  return parts.slice(0, 2).join('\n');
}

function axisLabelConfig(axis: Record<string, unknown>): Record<string, unknown> {
  return {
    color: '#64748b',
    margin: 16,
    interval: 0,
    hideOverlap: true,
    lineHeight: 15,
    formatter: formatCategoryLabel,
    ...((axis.axisLabel as Record<string, unknown>) ?? {}),
  };
}

function isHeatmapOption(option: Record<string, unknown>): boolean {
  const series = Array.isArray(option.series) ? option.series : [];
  return series.some((item) => (item as Record<string, unknown>)?.type === 'heatmap');
}

function axisCategoryCount(axis: unknown): number {
  if (!axis || Array.isArray(axis)) return 0;
  const data = (axis as Record<string, unknown>).data;
  return Array.isArray(data) ? data.length : 0;
}

function heatmapChartHeight(option: Record<string, unknown>, fallback: number): number {
  const xCount = axisCategoryCount(option.xAxis);
  const yCount = axisCategoryCount(option.yAxis);
  return Math.max(fallback, Math.min(560, 220 + yCount * 44 + Math.max(0, xCount - 4) * 10));
}

function withReadableHeatmap(option: Record<string, unknown>): Record<string, unknown> {
  if (!isHeatmapOption(option)) {
    return option;
  }

  const next = structuredClone(option);
  const grid = (next.grid ?? {}) as Record<string, unknown>;
  next.grid = {
    ...grid,
    left: 72,
    right: 36,
    top: 24,
    bottom: 96,
    containLabel: true,
  };

  const xAxisRaw = next.xAxis;
  const xAxes = Array.isArray(xAxisRaw) ? xAxisRaw : xAxisRaw ? [xAxisRaw] : [];
  next.xAxis = xAxes.map((axis) => ({
    ...(axis as Record<string, unknown>),
    axisLabel: axisLabelConfig(axis as Record<string, unknown>),
  }));

  const yAxisRaw = next.yAxis;
  const yAxes = Array.isArray(yAxisRaw) ? yAxisRaw : yAxisRaw ? [yAxisRaw] : [];
  next.yAxis = yAxes.map((axis) => ({
    ...(axis as Record<string, unknown>),
    axisLabel: {
      color: '#64748b',
      margin: 10,
      formatter:
        String((axis as Record<string, unknown>).type || '') === 'category'
          ? formatCategoryLabel
          : formatAxisNumber,
      ...(((axis as Record<string, unknown>).axisLabel as Record<string, unknown>) ?? {}),
    },
  }));

  const seriesRaw = Array.isArray(next.series) ? next.series : [];
  next.series = seriesRaw.map((item) => {
    const series = item as Record<string, unknown>;
    if (series.type !== 'heatmap') {
      return series;
    }
    const data = Array.isArray(series.data) ? series.data : [];
    return {
      ...series,
      progressive: 0,
      animation: false,
      label: {
        show: data.length <= 18,
        color: '#0f172a',
        fontSize: 10,
        formatter: ({ value }: { value: unknown }) =>
          Array.isArray(value) ? formatAxisNumber(value[2]) : formatAxisNumber(value),
        ...(series.label as Record<string, unknown> | undefined),
      },
      itemStyle: {
        borderColor: 'rgba(255,255,255,0.75)',
        borderWidth: 1,
        ...(series.itemStyle as Record<string, unknown> | undefined),
      },
    };
  });

  const visualMap = (next.visualMap ?? {}) as Record<string, unknown>;
  next.visualMap = {
    ...visualMap,
    show: false,
    orient: 'horizontal',
    left: 'center',
    bottom: 18,
    itemWidth: 220,
    itemHeight: 12,
    textStyle: { color: '#64748b', fontSize: 11 },
    calculable: false,
  };

  return next;
}

export function ChartRenderer({ option, height = 320, className }: ChartRendererProps) {
  if (!option || !option.series || (Array.isArray(option.series) && option.series.length === 0)) {
    return null;
  }

  const resolvedOption = withReadableHeatmap(option);
  const resolvedHeight = isHeatmapOption(resolvedOption)
    ? heatmapChartHeight(resolvedOption, height)
    : height;

  return (
    <div className={className ?? 'my-3 rounded-xl border border-gray-200 bg-surface p-5 shadow-card transition-shadow hover:shadow-card-hover'}>
      <ReactECharts
        option={resolvedOption}
        style={{ height: resolvedHeight, width: '100%' }}
        notMerge
        opts={{ renderer: 'canvas' }}
      />
    </div>
  );
}
