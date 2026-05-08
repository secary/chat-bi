import type { KpiCard as KpiCardType } from '../types/message';

interface KPICardsProps {
  cards: KpiCardType[];
}

const STATUS_STYLES: Record<string, string> = {
  success: 'bg-emerald-50 border-emerald-200 text-emerald-800',
  warning: 'bg-amber-50 border-amber-200 text-amber-800',
  danger: 'bg-red-50 border-red-200 text-red-800',
  neutral: 'bg-gray-50 border-gray-200 text-gray-800',
};

const STATUS_DOTS: Record<string, string> = {
  success: 'bg-emerald-500',
  warning: 'bg-amber-500',
  danger: 'bg-red-500',
  neutral: 'bg-gray-400',
};

export function KPICards({ cards }: KPICardsProps) {
  if (!cards || cards.length === 0) return null;

  return (
    <div className="my-4 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
      {cards.map((card, i) => (
        <div
          key={i}
          className={`rounded-xl border p-5 shadow-card transition-shadow hover:shadow-card-hover ${STATUS_STYLES[card.status] || STATUS_STYLES.neutral}`}
        >
          <div className="flex items-center gap-2">
            <span className={`h-2.5 w-2.5 rounded-full ${STATUS_DOTS[card.status] || STATUS_DOTS.neutral}`} />
            <span className="text-xs font-medium tracking-wide">{card.label}</span>
          </div>
          <p className="mt-1.5 text-2xl font-semibold tracking-tight">
            {card.value}
            {card.unit && <span className="ml-1.5 text-sm font-normal text-gray-400">{card.unit}</span>}
          </p>
        </div>
      ))}
    </div>
  );
}
