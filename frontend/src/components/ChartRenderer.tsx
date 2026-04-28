import ReactECharts from 'echarts-for-react';

interface ChartRendererProps {
  option: Record<string, unknown>;
}

export function ChartRenderer({ option }: ChartRendererProps) {
  if (!option || !option.series || (Array.isArray(option.series) && option.series.length === 0)) {
    return null;
  }

  return (
    <div className="my-3 rounded-lg border border-gray-200 bg-white p-4">
      <ReactECharts
        option={option}
        style={{ height: 320, width: '100%' }}
        notMerge
        opts={{ renderer: 'canvas' }}
      />
    </div>
  );
}
