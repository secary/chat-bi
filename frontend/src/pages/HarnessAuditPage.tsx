import { useEffect, useState } from 'react';
import { getHarnessAudit, listHarnessAuditCandidates } from '../api/client';
import type { HarnessAuditCandidate, HarnessAuditReport } from '../types/admin';
import { logger } from '../lib/logger';

export function HarnessAuditPage() {
  const [traceId, setTraceId] = useState('');
  const [recent, setRecent] = useState<HarnessAuditCandidate[]>([]);
  const [report, setReport] = useState<HarnessAuditReport | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const data = await listHarnessAuditCandidates();
        if (!cancelled) setRecent(data.items);
      } catch (e) {
        logger.error('harness-audits load', e);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const inspect = async (nextTraceId: string) => {
    const id = nextTraceId.trim();
    if (!id) return;
    setBusy(true);
    setError('');
    setTraceId(id);
    try {
      const data = await getHarnessAudit(id);
      setReport(data);
    } catch (e) {
      setReport(null);
      setError(e instanceof Error ? e.message : '加载审计报告失败');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex h-full flex-col gap-4 overflow-auto p-6 lg:p-8">
      <div>
        <h2 className="text-lg font-semibold tracking-tight text-gray-900">Harness 审计</h2>
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
            onClick={() => void inspect(traceId)}
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
                  onClick={() => void inspect(item.trace_id)}
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
              </div>
              <p className="text-gray-600">{report.summary}</p>
              <div>
                <p className="mb-2 text-xs font-semibold tracking-wide text-gray-500">问题列表</p>
                {report.issues.length === 0 ? (
                  <p className="text-sm text-emerald-600">未发现明显异常。</p>
                ) : (
                  <ul className="space-y-2">
                    {report.issues.map((issue) => (
                      <li key={`${issue.code}-${issue.message}`} className="rounded-lg border border-gray-100 px-3 py-2">
                        <div className="text-xs font-semibold text-gray-800">
                          {issue.code} · {issue.level}
                        </div>
                        <div className="mt-1 text-gray-600">{issue.message}</div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
