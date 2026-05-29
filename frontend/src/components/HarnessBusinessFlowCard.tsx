import type { HarnessBusinessFlowCard } from '../types/admin';

const FLOW_STATUS_STYLES: Record<string, string> = {
  completed: 'bg-emerald-100 text-emerald-700',
  warning: 'bg-amber-100 text-amber-700',
  error: 'bg-rose-100 text-rose-700',
  pending: 'bg-gray-100 text-gray-600',
};

const FLOW_STATUS_LABELS: Record<string, string> = {
  completed: '已就绪',
  warning: '需关注',
  error: '已阻塞',
  pending: '待继续',
};

export function HarnessBusinessFlowCardView({
  flow,
}: {
  flow: HarnessBusinessFlowCard;
}) {
  const badgeCls = FLOW_STATUS_STYLES[flow.status] || FLOW_STATUS_STYLES.pending;
  const badgeText = FLOW_STATUS_LABELS[flow.status] || FLOW_STATUS_LABELS.pending;

  return (
    <section className="rounded-2xl border border-gray-100 bg-white p-4 shadow-[0_10px_28px_rgba(15,23,42,0.04)]">
      <div className="flex flex-wrap items-center gap-2">
        <h4 className="text-sm font-semibold text-gray-900">{flow.title}</h4>
        <span className={`rounded-full px-2 py-1 text-[11px] font-medium ${badgeCls}`}>
          {badgeText}
        </span>
      </div>
      <p className="mt-2 text-sm text-gray-600">{flow.summary}</p>
      <ol className="mt-4 grid gap-2 md:grid-cols-2">
        {flow.steps.map((step, index) => {
          const stepCls = FLOW_STATUS_STYLES[step.status] || FLOW_STATUS_STYLES.pending;
          const stepText = FLOW_STATUS_LABELS[step.status] || FLOW_STATUS_LABELS.pending;
          return (
            <li key={step.key} className="rounded-xl border border-gray-100 bg-gray-50/70 p-3">
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-full bg-white px-2 py-1 text-[11px] font-mono text-gray-500">
                  {index + 1}
                </span>
                <span className="text-sm font-medium text-gray-800">{step.label}</span>
                <span className={`rounded-full px-2 py-1 text-[11px] font-medium ${stepCls}`}>
                  {stepText}
                </span>
              </div>
              <p className="mt-2 text-xs leading-5 text-gray-600">{step.detail}</p>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
