import type { ReactNode } from 'react';
import type { SessionRow } from '../types/admin';

interface ChatWelcomeHeroProps {
  title: string;
  children: ReactNode;
  sessions: SessionRow[];
  onSelectSession: (id: number) => void;
}

const cards = [
  {
    eyebrow: '中文问数',
    title: '多维分析',
    preview: 'table',
  },
  {
    eyebrow: '经营复盘',
    title: '管理建议',
    preview: 'list',
  },
  {
    eyebrow: '快速导入',
    title: 'Excel/CSV',
    preview: 'bars',
  },
  {
    eyebrow: '上传表',
    title: '指标提案',
    preview: 'proposal',
  },
  {
    eyebrow: '实时洞察',
    title: '仪表盘',
    preview: 'dashboard',
  },
];

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

      <div className="mt-14 grid w-full grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-5">
        {cards.map((card) => (
          <div
            key={card.title}
            className="rounded-2xl border border-gray-200 bg-white p-4 shadow-[0_16px_42px_rgba(15,23,42,0.06)]"
          >
            <div className="text-sm text-gray-400">{card.eyebrow}</div>
            <div className="mt-1 text-lg font-semibold text-gray-950">{card.title}</div>
            <CardPreview kind={card.preview} />
          </div>
        ))}
      </div>

      <div className="mt-12 w-full">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-900">最近</h3>
          <div className="flex gap-1.5 text-xs text-gray-400">
            <span className="rounded-md border border-gray-200 px-2 py-1">列表</span>
            <span className="rounded-md border border-gray-200 px-2 py-1">全部</span>
          </div>
        </div>
        <div className="overflow-hidden border-b border-gray-200">
          <div className="grid grid-cols-[minmax(0,1fr)_110px_130px] px-1 pb-3 text-xs text-gray-500">
            <span>标题</span>
            <span>类型</span>
            <span>最近访问</span>
          </div>
          {recent.length ? (
            recent.map((session) => (
              <button
                key={session.id}
                type="button"
                className="grid w-full grid-cols-[minmax(0,1fr)_110px_130px] border-t border-gray-100 px-1 py-3 text-left text-sm transition-colors hover:bg-gray-50"
                onClick={() => onSelectSession(session.id)}
              >
                <span className="truncate font-medium text-gray-800">{session.title}</span>
                <span className="text-gray-500">对话</span>
                <span className="truncate text-gray-500">{formatDate(session.updated_at)}</span>
              </button>
            ))
          ) : (
            <div className="border-t border-gray-100 px-1 py-5 text-sm text-gray-400">
              暂无最近会话
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function CardPreview({ kind }: { kind: string }) {
  if (kind === 'bars') {
    return (
      <div className="mt-5 flex h-24 items-end gap-2 rounded-lg border border-gray-100 bg-gray-50 px-4 pb-3">
        {[34, 58, 42, 76, 49, 64].map((h, idx) => (
          <span
            key={idx}
            className="w-3 rounded-t bg-emerald-400"
            style={{ height: `${h}%` }}
          />
        ))}
      </div>
    );
  }
  if (kind === 'dashboard') {
    return (
      <div className="mt-5 grid h-24 grid-cols-2 gap-2 rounded-lg border border-gray-100 bg-gray-50 p-3">
        <div className="rounded-md bg-blue-100" />
        <div className="rounded-md bg-indigo-100" />
        <div className="rounded-md bg-sky-100" />
        <div className="rounded-md bg-emerald-100" />
      </div>
    );
  }
  if (kind === 'proposal') {
    return (
      <div className="mt-5 h-24 rounded-lg border border-gray-100 bg-gray-50 p-3">
        <div className="mb-2 h-2 w-24 rounded bg-orange-200" />
        <div className="mb-2 h-2 w-16 rounded bg-gray-200" />
        <div className="h-12 rounded-md bg-[linear-gradient(135deg,#fed7aa,#fca5a5)]" />
      </div>
    );
  }
  if (kind === 'list') {
    return (
      <div className="mt-5 h-24 rounded-lg border border-gray-100 bg-gray-50 p-3">
        {[0, 1, 2, 3].map((idx) => (
          <div key={idx} className="mb-2 flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-accent/60" />
            <span className="h-2 flex-1 rounded bg-gray-200" />
          </div>
        ))}
      </div>
    );
  }
  return (
    <div className="mt-5 h-24 rounded-lg border border-gray-100 bg-gray-50 p-3">
      {[0, 1, 2, 3].map((row) => (
        <div key={row} className="mb-2 grid grid-cols-4 gap-2">
          {[0, 1, 2, 3].map((col) => (
            <span key={col} className="h-2 rounded bg-gray-200" />
          ))}
        </div>
      ))}
    </div>
  );
}

function formatDate(value: string | null): string {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value).slice(0, 10);
  return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' });
}
