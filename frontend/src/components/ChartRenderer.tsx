import ReactECharts from 'echarts-for-react';

interface ChartRendererProps {
  option: Record<string, unknown>;
}

export function ChartRenderer({ option }: ChartRendererProps) {
  if (!option || !option.series || (Array.isArray(option.series) && option.series.length === 0)) {
    return null;
  }

  return (
    <div className="my-3 rounded-xl border border-gray-200 bg-surface p-5 shadow-card transition-shadow hover:shadow-card-hover">
      <ReactECharts
        option={option}
        style={{ height: 320, width: '100%' }}
        notMerge
        opts={{ renderer: 'canvas' }}
      />
    </div>
  );
}
