import { useCallback, useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { getHarnessAudit, listHarnessAuditCandidates } from '../api/client';
import { HarnessBusinessFlowCardView } from '../components/HarnessBusinessFlowCard';
import { HarnessDebugTimeline } from '../components/HarnessDebugTimeline';
import type { HarnessAuditCandidate, HarnessAuditReport } from '../types/admin';
import { keywordForIssue } from '../lib/auditDebug';
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

  const jumpToIssueDebug = useCallback((code: string, keyword: string) => {
    setShowDebug(true);
    setEventQuery(keyword);
    queueMicrotask(() => {
      const el = document.getElementById(`issue-${code}`);
      el?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    });
  }, []);

  return (
    <div className="flex h-full min-h-0 flex-col bg-white">
      <header className="bg-white px-6 py-7">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-5">
          <div>
            <h2 className="text-[26px] font-semibold leading-tight tracking-normal text-gray-950">审计</h2>
            <p className="mt-1 text-xs text-gray-500">
              按 trace_id 查看全链路自检结果，快速判断动作漂移、约束拒绝、skill 失败或步数耗尽。
            </p>
          </div>
          <div className="flex flex-wrap gap-3 rounded-[28px] border border-gray-200 bg-white p-3 shadow-[0_18px_55px_rgba(15,23,42,0.08)]">
            <input
              className="min-w-[280px] flex-1 rounded-full border border-transparent bg-gray-50 px-4 py-2.5 text-sm transition-all placeholder:text-gray-400 focus:border-accent focus:bg-white focus:outline-none focus:ring-2 focus:ring-accent/30"
              placeholder="输入 trace_id"
              value={traceId}
              onChange={(e) => setTraceId(e.target.value)}
            />
            <button
              type="button"
              className="rounded-full bg-accent px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-hover disabled:opacity-50"
              disabled={busy || !traceId.trim()}
              onClick={() => void inspectTrace(traceId)}
            >
              {busy ? '分析中…' : '查看审计'}
            </button>
          </div>
          {error ? <p className="text-sm text-red-600">{error}</p> : null}
        </div>
      </header>

      <div className="min-h-0 flex-1 overflow-auto px-6 pb-8 lg:px-8">
        <div className="mx-auto grid w-full max-w-6xl gap-5 lg:grid-cols-[320px_minmax(0,1fr)]">
          <section className="min-h-0 rounded-2xl border border-gray-200 bg-white p-4 shadow-[0_16px_42px_rgba(15,23,42,0.06)]">
            <div className="mb-3 flex items-center justify-between gap-2">
              <h3 className="text-sm font-semibold text-gray-900">最近 Trace</h3>
              <span className="text-xs text-gray-400">{recent.length}</span>
            </div>
            <ul className="max-h-[calc(100vh-230px)] space-y-1 overflow-auto pr-1">
              {recent.map((item) => (
                <li key={item.trace_id}>
                  <button
                    type="button"
                    className="w-full rounded-xl border border-transparent px-3 py-2.5 text-left text-xs transition-colors hover:border-gray-200 hover:bg-gray-50"
                    onClick={() => void inspectTrace(item.trace_id)}
                  >
                    <div className="truncate font-mono font-medium text-gray-800">{item.trace_id}</div>
                    <div className="mt-1 text-gray-400">events · {item.event_count}</div>
                  </button>
                </li>
              ))}
              {recent.length === 0 ? (
                <li className="px-2.5 py-4 text-sm text-gray-400">暂无可审计 trace</li>
              ) : null}
            </ul>
          </section>

          {!report ? (
            <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-[0_16px_42px_rgba(15,23,42,0.06)]">
              <h3 className="text-sm font-semibold text-gray-900">审计结果</h3>
              <p className="mt-3 text-sm text-gray-400">选择一个 trace 查看自检结果。</p>
            </section>
          ) : (
            <div className="grid items-stretch gap-4 xl:grid-cols-[minmax(0,1.16fr)_minmax(380px,0.84fr)]">
              <section className="h-full rounded-2xl border border-gray-200 bg-white p-5 shadow-[0_16px_42px_rgba(15,23,42,0.06)]">
                <div className="flex items-center justify-between gap-3">
                  <h3 className="text-sm font-semibold text-gray-900">审计结果</h3>
                  <span className="rounded-full border border-gray-200 px-2.5 py-1 text-xs text-gray-600">
                    {report.status}
                  </span>
                </div>
                <div className="mt-3 space-y-4 text-sm">
                  <div className="flex flex-wrap gap-3">
                    <span className="rounded-full bg-gray-50 px-3 py-1 font-mono text-xs text-gray-700">
                      {report.trace_id}
                    </span>
                    <span className="rounded-full bg-gray-50 px-3 py-1 text-xs text-gray-700">评分：{report.score}</span>
                    <span className="rounded-full bg-gray-50 px-3 py-1 text-xs text-gray-700">events：{report.event_count}</span>
                  </div>
                  <p className="text-gray-600">{report.summary}</p>
                  <div className="space-y-4">
                    {report.business_flows.length > 0 ? (
                      <div>
                        <p className="mb-2 text-xs font-semibold tracking-wide text-gray-500">业务链路状态</p>
                        <div className="space-y-3">
                          {report.business_flows.map((flow) => <HarnessBusinessFlowCardView key={flow.flow_key} flow={flow} />)}
                        </div>
                      </div>
                    ) : (
                      <section className="rounded-2xl border border-dashed border-gray-200 bg-gray-50/70 p-4">
                        <p className="text-sm text-gray-600">当前 trace 暂无可汇总的业务链路状态。</p>
                      </section>
                    )}
                    <div>
                      <p className="mb-2 text-xs font-semibold tracking-wide text-gray-500">问题列表</p>
                      {report.issues.length === 0 ? (
                        <p className="text-sm text-emerald-600">未发现明显异常。</p>
                      ) : (
                        <ul className="space-y-2">
                          {report.issues.map((issue) => (
                            <li
                              key={`${issue.code}-${issue.message}`}
                              className="rounded-2xl border border-gray-100 bg-white px-3 py-2 shadow-[0_10px_28px_rgba(15,23,42,0.04)]"
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
                  </div>
                </div>
              </section>
              <HarnessDebugTimeline
                events={report.events}
                showDebug={showDebug}
                eventQuery={eventQuery}
                onToggle={() => setShowDebug((value) => !value)}
                onQueryChange={setEventQuery}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
