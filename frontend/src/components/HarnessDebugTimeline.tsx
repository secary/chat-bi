import type { HarnessAuditEvent } from '../types/admin';
import {
  auditEventTone,
  filterAuditEvents,
  formatAuditPayload,
  summarizeAuditEvent,
} from '../lib/auditDebug';

function toneCardClass(event: HarnessAuditEvent) {
  const tone = auditEventTone(event);
  if (tone === 'critical') return 'rounded-lg border border-rose-200 bg-rose-50/70 p-3';
  if (tone === 'warning') return 'rounded-lg border border-amber-200 bg-amber-50/70 p-3';
  return 'rounded-lg border border-gray-200 bg-white p-3';
}

function toneBadgeClass(event: HarnessAuditEvent) {
  const tone = auditEventTone(event);
  if (tone === 'critical') return 'rounded-full bg-rose-100 px-2 py-1 text-rose-700';
  if (tone === 'warning') return 'rounded-full bg-amber-100 px-2 py-1 text-amber-700';
  return 'rounded-full bg-gray-100 px-2 py-1 text-gray-500';
}

function toneLabel(event: HarnessAuditEvent) {
  const tone = auditEventTone(event);
  if (tone === 'critical') return '关键事件';
  if (tone === 'warning') return '关注事件';
  return '普通事件';
}

export function HarnessDebugTimeline({
  events,
  showDebug,
  eventQuery,
  onToggle,
  onQueryChange,
}: {
  events: HarnessAuditEvent[];
  showDebug: boolean;
  eventQuery: string;
  onToggle: () => void;
  onQueryChange: (value: string) => void;
}) {
  const debugEvents = filterAuditEvents(events, eventQuery);

  return (
    <section className="flex h-full min-h-[720px] flex-col rounded-2xl border border-sky-200/80 bg-[linear-gradient(180deg,rgba(239,246,255,0.95),rgba(255,255,255,0.98))] p-4 shadow-[0_18px_42px_-28px_rgba(37,99,235,0.35)]">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-sky-100 bg-white/75 px-4 py-3 backdrop-blur">
        <div>
          <p className="text-xs font-semibold tracking-[0.28em] text-sky-700">DEBUG 时间线</p>
          <p className="mt-1 text-sm text-gray-600">快速筛查拒绝、空结果、依赖断点和决策审核事件。</p>
        </div>
        <button
          type="button"
          className={
            showDebug
              ? 'rounded-xl border border-sky-500/40 bg-sky-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-sky-500'
              : 'rounded-xl border border-sky-300 bg-sky-50 px-4 py-2 text-sm font-semibold text-sky-700 shadow-sm transition hover:bg-sky-100'
          }
          onClick={onToggle}
        >
          {showDebug ? '收起 Debug 事件' : `展开 Debug 事件 · ${events.length}`}
        </button>
      </div>

      {showDebug ? (
        <div className="mt-4 flex min-h-0 flex-1 flex-col">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full bg-white px-2.5 py-1 text-[11px] text-sky-700 shadow-sm">
              当前显示 {debugEvents.length} / {events.length}
            </span>
          </div>
          <div className="mt-3">
            <input
              className="w-full rounded-xl border border-sky-100 bg-white/90 px-3 py-2 text-sm shadow-sm outline-none transition placeholder:text-gray-400 focus:border-sky-300"
              placeholder="按 event_name / agent / skill / reason / payload 搜索"
              value={eventQuery}
              onChange={(e) => onQueryChange(e.target.value)}
            />
          </div>
          {debugEvents.length === 0 ? (
            <p className="mt-3 text-sm text-gray-400">没有匹配的调试事件。</p>
          ) : (
            <ol className="mt-3 min-h-0 flex-1 space-y-3 overflow-auto pr-1">
              {debugEvents.map((event, index) => (
                <li
                  id={`issue-${event.event_name}`}
                  key={`${event.id}-${event.event_name}-${index}`}
                  className={toneCardClass(event)}
                >
                  <div className="flex flex-wrap items-center gap-2 text-xs">
                    <span className="rounded-full bg-gray-100 px-2 py-1 font-mono text-gray-700">
                      #{index + 1}
                    </span>
                    <span className="rounded-full bg-gray-100 px-2 py-1 font-mono text-gray-700">
                      {event.span_name}
                    </span>
                    <span className="rounded-full bg-gray-100 px-2 py-1 font-mono text-gray-700">
                      {event.event_name}
                    </span>
                    <span className={toneBadgeClass(event)}>{toneLabel(event)}</span>
                    <span className="rounded-full bg-gray-100 px-2 py-1 text-gray-500">
                      {event.created_at}
                    </span>
                  </div>
                  <p className="mt-2 text-sm font-medium text-gray-800">
                    {summarizeAuditEvent(event)}
                  </p>
                  {event.message ? (
                    <p className="mt-1 text-sm text-gray-600">{event.message}</p>
                  ) : null}
                  <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-gray-500">
                    {typeof event.payload.step === 'number' ? (
                      <span className="rounded-full bg-gray-50 px-2 py-1">
                        step={String(event.payload.step)}
                      </span>
                    ) : null}
                    {typeof event.payload.round === 'number' ? (
                      <span className="rounded-full bg-gray-50 px-2 py-1">
                        round={String(event.payload.round)}
                      </span>
                    ) : null}
                    {typeof event.payload.task_index === 'number' ? (
                      <span className="rounded-full bg-gray-50 px-2 py-1">
                        task={String(event.payload.task_index)}
                      </span>
                    ) : null}
                    {typeof event.payload.ok === 'boolean' ? (
                      <span className="rounded-full bg-gray-50 px-2 py-1">
                        ok={String(event.payload.ok)}
                      </span>
                    ) : null}
                  </div>
                  <details className="mt-3">
                    <summary className="cursor-pointer text-xs font-medium text-gray-500">
                      查看原始 payload
                    </summary>
                    <pre className="mt-2 overflow-x-auto rounded-lg bg-gray-950 p-3 text-xs text-gray-100">
                      {formatAuditPayload(event.payload)}
                    </pre>
                  </details>
                </li>
              ))}
            </ol>
          )}
        </div>
      ) : (
        <div className="mt-4 flex min-h-0 flex-1 items-start">
          <div className="w-full rounded-2xl border border-dashed border-sky-200 bg-white/65 p-4">
          <p className="text-sm text-gray-600">点击右上角按钮展开完整 Debug 时间线。</p>
          <p className="mt-1 text-xs text-gray-400">
            适合排查 `policy_rejected`、`decision_content_audited`、空 observation 等细节。
          </p>
          </div>
        </div>
      )}
    </section>
  );
}
