import { useEffect, useState } from 'react';
import type { ThinkingStep } from '../types/message';

interface ThinkingBubbleProps {
  completedAt?: string;
  elapsedMs?: number;
  startedAt?: string;
  steps: ThinkingStep[];
}

function stepMessage(step: ThinkingStep): string {
  return typeof step === 'string' ? step : step.message;
}

function stepDetails(step: ThinkingStep) {
  return typeof step === 'string' ? [] : step.details || [];
}

function formatElapsed(ms: number): string {
  const totalSeconds = Math.max(0, Math.floor(ms / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (minutes > 0) {
    return `${minutes}分${String(seconds).padStart(2, '0')}秒`;
  }
  return `${seconds}秒`;
}

export function ThinkingBubble({
  completedAt,
  elapsedMs,
  startedAt,
  steps,
}: ThinkingBubbleProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const [now, setNow] = useState(() => Date.now());
  const safeActiveIndex =
    steps.length > 0 ? Math.min(activeIndex, steps.length - 1) : 0;

  useEffect(() => {
    if (collapsed || safeActiveIndex >= steps.length - 1) return;

    const timer = window.setTimeout(() => {
      setActiveIndex((currentIndex) =>
        Math.min(currentIndex + 1, steps.length - 1),
      );
    }, 900);

    return () => window.clearTimeout(timer);
  }, [collapsed, safeActiveIndex, steps.length]);

  useEffect(() => {
    if (collapsed || completedAt || !startedAt) return;
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [collapsed, completedAt, startedAt]);

  const startedMs = startedAt ? new Date(startedAt).getTime() : NaN;
  const liveElapsedMs =
    Number.isNaN(startedMs) || completedAt ? undefined : now - startedMs;
  const displayElapsedMs = elapsedMs ?? liveElapsedMs;
  if (steps.length === 0 && displayElapsedMs == null) return null;
  const activeStep = steps[safeActiveIndex] || steps[steps.length - 1] || '';
  const details = stepDetails(activeStep);
  const elapsedText =
    displayElapsedMs == null ? '' : formatElapsed(displayElapsedMs);

  return (
    <div className="mb-3 rounded-xl border border-gray-200/60 bg-gray-50/70 px-4 py-2.5 shadow-sm shadow-gray-100/60">
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="flex items-center gap-1 text-sm text-gray-500 transition-colors hover:text-gray-700"
      >
        <span className="text-xs">{collapsed ? '▶' : '▼'}</span>
        <span>处理进度 ({steps.length})</span>
      </button>
      {!collapsed && (
        <div
          key={`${safeActiveIndex}-${stepMessage(activeStep)}`}
          className="mt-2 text-sm leading-relaxed text-gray-600"
        >
          <span className="min-w-0 flex-1">
            {completedAt ? (
              <span className="text-gray-500">
                已处理完毕{elapsedText ? ` · 耗时 ${elapsedText}` : ''}
              </span>
            ) : (
              <span>
                <span className="animate-pulse">{stepMessage(activeStep)}</span>
                {elapsedText ? (
                  <span className="ml-2 text-xs text-gray-400">{elapsedText}</span>
                ) : null}
              </span>
            )}
            {!completedAt && details.length > 0 ? (
              <span className="mt-1 block space-y-1">
                {details.map((detail, detailIndex) => (
                  <details
                    key={`${detail.title}-${detailIndex}`}
                    className="rounded-lg border border-gray-200 bg-white/80 px-2 py-1"
                  >
                    <summary className="cursor-pointer select-none text-xs text-gray-500">
                      {detail.title}
                    </summary>
                    <pre className="mt-1 overflow-x-auto whitespace-pre-wrap break-words rounded-md bg-gray-950 px-2 py-1.5 text-xs leading-relaxed text-gray-100">
                      <code>{detail.content}</code>
                    </pre>
                  </details>
                ))}
              </span>
            ) : null}
          </span>
        </div>
      )}
    </div>
  );
}
