import ReactECharts from 'echarts-for-react';

interface ChartRendererProps {
  option: Record<string, unknown>;
  height?: number;
  className?: string;
}

export function ChartRenderer({ option, height = 320, className }: ChartRendererProps) {
  if (!option || !option.series || (Array.isArray(option.series) && option.series.length === 0)) {
    return null;
  }

  return (
    <div className={className ?? 'my-3 rounded-xl border border-gray-200 bg-surface p-5 shadow-card transition-shadow hover:shadow-card-hover'}>
      <ReactECharts
        option={option}
        style={{ height, width: '100%' }}
        notMerge
        opts={{ renderer: 'canvas' }}
      />
    </div>
  );
}
