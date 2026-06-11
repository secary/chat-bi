import type { ReactNode } from 'react';
import type { SessionRow } from '../types/admin';

interface ChatWelcomeHeroProps {
  title: string;
  children: ReactNode;
  sessions: SessionRow[];
  onSelectSession: (id: number) => void;
}

export function ChatWelcomeHero({
  title,
  children,
  sessions,
  onSelectSession,
}: ChatWelcomeHeroProps) {
  const recent = sessions.slice(0, 5);
  return (
    <div className="flex w-full max-w-6xl flex-col items-center">
      <div className="relative w-full max-w-4xl pt-7 text-center">
        <div className="pointer-events-none absolute inset-x-8 top-14 h-20 rounded-full bg-[linear-gradient(90deg,rgba(20,184,166,0.12),rgba(99,102,241,0.14),rgba(244,114,182,0.10))] blur-2xl" />
        <h2 className="relative text-[28px] font-semibold leading-tight tracking-normal text-gray-950 md:text-[34px]">
          {title}
          <span className="ml-2 text-accent">多维分析</span>
        </h2>
        <div className="relative mt-8 w-full">{children}</div>
      </div>

      <div className="mt-12 w-full">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-900">最近会话</h3>
          <span className="text-xs text-gray-400">{recent.length} 条</span>
        </div>
        <div className="overflow-hidden border-y border-gray-200">
          {recent.length ? (
            recent.map((session) => (
              <button
                key={session.id}
                type="button"
                className="grid min-h-16 w-full grid-cols-[minmax(0,1fr)_auto] items-center gap-3 border-b border-gray-100 px-1 py-3 text-left transition-colors last:border-b-0 hover:bg-gray-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/25"
                onClick={() => onSelectSession(session.id)}
              >
                <span className="min-w-0">
                  <span className="block truncate text-sm font-medium text-gray-900">
                    {session.title || '新聊天'}
                  </span>
                  <span className="mt-1 block truncate text-xs text-gray-500">
                    对话 · 最近访问 {formatDate(session.updated_at)}
                  </span>
                </span>
                <span className="flex items-center gap-2 pl-3 text-xs text-gray-400">
                  <span className="hidden sm:inline">{formatRelativeDate(session.updated_at)}</span>
                  <span aria-hidden="true" className="text-base leading-none text-gray-300">
                    ›
                  </span>
                </span>
              </button>
            ))
          ) : (
            <div className="px-1 py-8 text-center text-sm text-gray-400">
              暂无最近会话
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function formatDate(value: string | null): string {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value).slice(0, 10);
  return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' });
}

function formatRelativeDate(value: string | null): string {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  const today = new Date();
  const startOfToday = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const startOfDate = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  const diffDays = Math.round(
    (startOfToday.getTime() - startOfDate.getTime()) / (24 * 60 * 60 * 1000),
  );
  if (diffDays === 0) return '今天';
  if (diffDays === 1) return '昨天';
  if (diffDays > 1 && diffDays < 7) return `${diffDays} 天前`;
  return formatDate(value);
}
