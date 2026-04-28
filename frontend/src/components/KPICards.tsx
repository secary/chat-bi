import type { KpiCard as KpiCardType } from '../types/message';

interface KPICardsProps {
  cards: KpiCardType[];
}

const STATUS_STYLES: Record<string, string> = {
  success: 'bg-green-50 border-green-200 text-green-800',
  warning: 'bg-yellow-50 border-yellow-200 text-yellow-800',
  danger: 'bg-red-50 border-red-200 text-red-800',
  neutral: 'bg-gray-50 border-gray-200 text-gray-800',
};

const STATUS_DOTS: Record<string, string> = {
  success: 'bg-green-500',
  warning: 'bg-yellow-500',
  danger: 'bg-red-500',
  neutral: 'bg-gray-400',
};

export function KPICards({ cards }: KPICardsProps) {
  if (!cards || cards.length === 0) return null;

  return (
    <div className="my-3 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
      {cards.map((card, i) => (
        <div
          key={i}
          className={`rounded-lg border p-4 ${STATUS_STYLES[card.status] || STATUS_STYLES.neutral}`}
        >
          <div className="flex items-center gap-2">
            <span className={`h-2 w-2 rounded-full ${STATUS_DOTS[card.status] || STATUS_DOTS.neutral}`} />
            <span className="text-xs font-medium">{card.label}</span>
          </div>
          <p className="mt-1 text-xl font-semibold">
            {card.value}
            {card.unit && <span className="ml-1 text-sm font-normal opacity-70">{card.unit}</span>}
          </p>
        </div>
      ))}
    </div>
  );
}
