import { useCallback, useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { getHarnessAudit, listHarnessAuditCandidates } from '../api/client';
import type { HarnessAuditCandidate, HarnessAuditReport } from '../types/admin';
import {
  auditEventTone,
  filterAuditEvents,
  formatAuditPayload,
  keywordForIssue,
  summarizeAuditEvent,
} from '../lib/auditDebug';
import { logger } from '../lib/logger';

export function HarnessAuditPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialTraceId = searchParams.get('trace_id') || '';
  const initialTraceIdRef = useRef(initialTraceId || '');
  const [traceId, setTraceId] = useState(initialTraceId);
  const [recent, setRecent] = useState<HarnessAuditCandidate[]>([]);
  const [report, setReport] = useState<HarnessAuditReport | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [showDebug, setShowDebug] = useState(false);
  const [eventQuery, setEventQuery] = useState('');

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const data = await listHarnessAuditCandidates();
        if (!cancelled) setRecent(data.items);
      } catch (e) {
        logger.error('audits load', e);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const inspectTrace = useCallback(async (nextTraceId: string, updateUrl = true) => {
    const id = nextTraceId.trim();
    if (!id) return;
    setBusy(true);
    setError('');
    setTraceId(id);
    if (updateUrl) {
      setSearchParams({ trace_id: id });
    }
    try {
      const data = await getHarnessAudit(id);
      setReport(data);
    } catch (e) {
      setReport(null);
      setError(e instanceof Error ? e.message : '加载审计报告失败');
    } finally {
      setBusy(false);
    }
  }, [setSearchParams]);

  useEffect(() => {
    const incoming = initialTraceIdRef.current;
    if (!incoming) return;
    queueMicrotask(() => {
      void inspectTrace(incoming, false);
      initialTraceIdRef.current = '';
    });
  }, [inspectTrace]);

  const debugEvents = report ? filterAuditEvents(report.events, eventQuery) : [];

  const jumpToIssueDebug = useCallback((code: string, keyword: string) => {
    setShowDebug(true);
    setEventQuery(keyword);
    queueMicrotask(() => {
      const el = document.getElementById(`issue-${code}`);
      el?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    });
  }, []);

  return (
    <div className="flex h-full flex-col gap-4 overflow-auto p-6 lg:p-8">
      <div>
        <h2 className="text-lg font-semibold tracking-tight text-gray-900">审计</h2>
        <p className="mt-1 text-xs text-gray-500">
          按 trace_id 查看全链路自检结果，快速判断是否存在动作漂移、约束拒绝、skill 失败或步数耗尽。
        </p>
      </div>

      <div className="rounded-xl border border-gray-200 bg-surface p-4 shadow-card">
        <div className="flex flex-wrap gap-2">
          <input
            className="min-w-[280px] flex-1 rounded-lg border border-gray-200 px-3 py-2 text-sm"
            placeholder="输入 trace_id"
            value={traceId}
            onChange={(e) => setTraceId(e.target.value)}
          />
          <button
            type="button"
            className="rounded-lg bg-accent px-4 py-2 text-sm text-white disabled:opacity-50"
            disabled={busy || !traceId.trim()}
            onClick={() => void inspectTrace(traceId)}
          >
            {busy ? '分析中…' : '查看审计'}
          </button>
        </div>
        {error ? <p className="mt-2 text-sm text-red-600">{error}</p> : null}
      </div>

      <div className="grid gap-4 lg:grid-cols-[320px_minmax(0,1fr)]">
        <section className="rounded-xl border border-gray-200 bg-surface p-4 shadow-card">
          <h3 className="text-sm font-semibold text-gray-900">最近 Trace</h3>
          <ul className="mt-3 space-y-2">
            {recent.map((item) => (
              <li key={item.trace_id}>
                <button
                  type="button"
                  className="w-full rounded-lg border border-gray-100 px-3 py-2 text-left text-xs hover:bg-gray-50"
                  onClick={() => void inspectTrace(item.trace_id)}
                >
                  <div className="truncate font-mono text-gray-800">{item.trace_id}</div>
                  <div className="mt-1 text-gray-400">events: {item.event_count}</div>
                </button>
              </li>
            ))}
          </ul>
        </section>

        <section className="rounded-xl border border-gray-200 bg-surface p-4 shadow-card">
          <h3 className="text-sm font-semibold text-gray-900">审计结果</h3>
          {!report ? (
            <p className="mt-3 text-sm text-gray-400">选择一个 trace 查看自检结果。</p>
          ) : (
            <div className="mt-3 space-y-4 text-sm">
              <div className="flex flex-wrap gap-3">
                <span className="rounded-full bg-gray-100 px-3 py-1 font-mono text-xs text-gray-700">
                  {report.trace_id}
                </span>
                <span className="rounded-full bg-gray-100 px-3 py-1 text-xs text-gray-700">
                  状态：{report.status}
                </span>
                <span className="rounded-full bg-gray-100 px-3 py-1 text-xs text-gray-700">
                  评分：{report.score}
                </span>
                <span className="rounded-full bg-gray-100 px-3 py-1 text-xs text-gray-700">
                  events：{report.event_count}
                </span>
                <button
                  type="button"
                  className="rounded-full border border-gray-200 px-3 py-1 text-xs text-gray-700 hover:bg-gray-50"
                  onClick={() => setShowDebug((value) => !value)}
                >
                  {showDebug ? '隐藏 Debug 事件' : '显示 Debug 事件'}
                </button>
              </div>
              <p className="text-gray-600">{report.summary}</p>
              <div>
                <p className="mb-2 text-xs font-semibold tracking-wide text-gray-500">问题列表</p>
                {report.issues.length === 0 ? (
                  <p className="text-sm text-emerald-600">未发现明显异常。</p>
                ) : (
                  <ul className="space-y-2">
                    {report.issues.map((issue) => (
                      <li
                        key={`${issue.code}-${issue.message}`}
                        className="rounded-lg border border-gray-100 px-3 py-2"
                      >
                        <div className="text-xs font-semibold text-gray-800">
                          {issue.code} · {issue.level}
                        </div>
                        <div className="mt-1 text-gray-600">{issue.message}</div>
                        <button
                          type="button"
                          className="mt-2 rounded-full border border-gray-200 px-2 py-1 text-[11px] text-gray-600 hover:bg-gray-50"
                          onClick={() => jumpToIssueDebug(issue.code, keywordForIssue(issue))}
                        >
                          查看相关 Debug 事件
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              {showDebug ? (
                <div className="rounded-xl border border-gray-100 bg-gray-50/70 p-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-xs font-semibold tracking-wide text-gray-500">
                      Debug 时间线
                    </p>
                    <span className="rounded-full bg-white px-2 py-1 text-[11px] text-gray-500">
                      当前显示 {debugEvents.length} / {report.events.length}
                    </span>
                  </div>
                  <div className="mt-3">
                    <input
                      className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm"
                      placeholder="按 event_name / agent / skill / reason / payload 搜索"
                      value={eventQuery}
                      onChange={(e) => setEventQuery(e.target.value)}
                    />
                  </div>
                  {debugEvents.length === 0 ? (
                    <p className="mt-3 text-sm text-gray-400">没有匹配的调试事件。</p>
                  ) : (
                    <ol className="mt-3 space-y-3">
                      {debugEvents.map((event, index) => (
                        <li
                          id={`issue-${event.event_name}`}
                          key={`${event.id}-${event.event_name}-${index}`}
                          className={
                            auditEventTone(event) === 'critical'
                              ? 'rounded-lg border border-rose-200 bg-rose-50/70 p-3'
                              : auditEventTone(event) === 'warning'
                                ? 'rounded-lg border border-amber-200 bg-amber-50/70 p-3'
                                : 'rounded-lg border border-gray-200 bg-white p-3'
                          }
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
                            <span
                              className={
                                auditEventTone(event) === 'critical'
                                  ? 'rounded-full bg-rose-100 px-2 py-1 text-rose-700'
                                  : auditEventTone(event) === 'warning'
                                    ? 'rounded-full bg-amber-100 px-2 py-1 text-amber-700'
                                    : 'rounded-full bg-gray-100 px-2 py-1 text-gray-500'
                              }
                            >
                              {auditEventTone(event) === 'critical'
                                ? '关键事件'
                                : auditEventTone(event) === 'warning'
                                  ? '关注事件'
                                  : '普通事件'}
                            </span>
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
              ) : null}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
