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

        {!report ? (
          <section className="rounded-xl border border-gray-200 bg-surface p-4 shadow-card">
            <h3 className="text-sm font-semibold text-gray-900">审计结果</h3>
            <p className="mt-3 text-sm text-gray-400">选择一个 trace 查看自检结果。</p>
          </section>
        ) : (
          <div className="grid items-stretch gap-4 xl:grid-cols-[minmax(0,1.16fr)_minmax(380px,0.84fr)]">
            <section className="h-full rounded-xl border border-gray-200 bg-surface p-4 shadow-card">
              <h3 className="text-sm font-semibold text-gray-900">审计结果</h3>
              <div className="mt-3 space-y-4 text-sm">
                <div className="flex flex-wrap gap-3">
                  <span className="rounded-full bg-gray-100 px-3 py-1 font-mono text-xs text-gray-700">
                    {report.trace_id}
                  </span>
                  <span className="rounded-full bg-gray-100 px-3 py-1 text-xs text-gray-700">状态：{report.status}</span>
                  <span className="rounded-full bg-gray-100 px-3 py-1 text-xs text-gray-700">评分：{report.score}</span>
                  <span className="rounded-full bg-gray-100 px-3 py-1 text-xs text-gray-700">events：{report.event_count}</span>
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
                    <section className="rounded-xl border border-dashed border-gray-200 bg-gray-50/70 p-4">
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
  );
}
