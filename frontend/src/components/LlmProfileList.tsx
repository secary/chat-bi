import type { LlmProfilePublic } from '../types/admin';
import { healthStatusLabel, profileListTitle } from '../lib/llmProfileUi';

function healthClasses(status: string): string {
  if (status === 'ok') return 'border-emerald-200 bg-emerald-50 text-emerald-800';
  if (status === 'error') return 'border-red-200 bg-red-50 text-red-800';
  return 'border-gray-200 bg-gray-50 text-gray-600';
}

export interface LlmProfileListProps {
  profiles: LlmProfilePublic[];
  activeProfileId: number | null;
  selectedKey: number | 'new';
  busyTest: 'all' | number | null;
  onSelect: (id: number) => void;
  onSelectNew: () => void;
  onActivate: (id: number) => void;
  onDelete: (id: number) => void;
  onTest: (id: number) => void;
  onTestAll: () => void;
  onMove: (id: number, dir: 'up' | 'down') => void;
}

export function LlmProfileList({
  profiles,
  activeProfileId,
  selectedKey,
  busyTest,
  onSelect,
  onSelectNew,
  onActivate,
  onDelete,
  onTest,
  onTestAll,
  onMove,
}: LlmProfileListProps) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-2">
        <div className="text-sm font-medium text-gray-900">已保存的模型</div>
        <button
          type="button"
          onClick={() => onTestAll()}
          disabled={profiles.length === 0 || busyTest !== null}
          className="rounded-full border border-gray-200 bg-white px-2.5 py-1 text-xs text-gray-600 hover:bg-gray-50 disabled:opacity-50"
        >
          {busyTest === 'all' ? '检测中…' : '全部检测'}
        </button>
      </div>
      <button
        type="button"
        onClick={() => onSelectNew()}
        className={
          'w-full rounded-lg border px-3 py-2 text-left text-sm transition-colors ' +
          (selectedKey === 'new'
            ? 'border-accent bg-accent-light text-accent'
            : 'border-gray-200 bg-white text-gray-700 hover:bg-gray-50')
        }
      >
        + 新增模型配置
      </button>
      <ul className="space-y-2">
        {profiles.map((p, idx) => {
          const title = profileListTitle(p.display_name, p.model);
          const selected = selectedKey !== 'new' && selectedKey === p.id;
          return (
            <li key={p.id}>
              <div
                className={
                  'rounded-lg border p-3 text-sm shadow-card transition-colors ' +
                  (selected ? 'border-accent bg-accent-light/40' : 'border-gray-200 bg-white')
                }
              >
                <button type="button" onClick={() => onSelect(p.id)} className="w-full text-left">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <div className="truncate font-medium text-gray-900">{title}</div>
                      <div className="mt-0.5 truncate text-xs text-gray-500">{p.model}</div>
                      {p.api_base ? (
                        <div className="mt-0.5 truncate text-xs text-gray-400">{p.api_base}</div>
                      ) : null}
                    </div>
                    <span
                      className={
                        'shrink-0 rounded-full border px-2 py-0.5 text-[10px] ' +
                        healthClasses(p.health_status || 'unknown')
                      }
                    >
                      {healthStatusLabel(p.health_status || 'unknown')}
                    </span>
                  </div>
                </button>
                <label className="mt-2 flex cursor-pointer items-center gap-2 text-xs text-gray-600">
                  <input
                    type="radio"
                    name="llm-active"
                    checked={activeProfileId === p.id}
                    onChange={() => onActivate(p.id)}
                    className="accent-accent"
                  />
                  对话默认使用该模型
                </label>
                {p.health_detail && p.health_status === 'error' ? (
                  <div className="mt-2 rounded border border-red-100 bg-red-50/80 px-2 py-1 text-[11px] text-red-800">
                    {p.health_detail}
                  </div>
                ) : null}
                <div className="mt-2 flex flex-wrap gap-1.5">
                  <button
                    type="button"
                    onClick={() => onMove(p.id, 'up')}
                    disabled={idx === 0}
                    className="rounded border border-gray-200 px-2 py-0.5 text-xs text-gray-600 hover:bg-gray-50 disabled:opacity-40"
                  >
                    上移
                  </button>
                  <button
                    type="button"
                    onClick={() => onMove(p.id, 'down')}
                    disabled={idx >= profiles.length - 1}
                    className="rounded border border-gray-200 px-2 py-0.5 text-xs text-gray-600 hover:bg-gray-50 disabled:opacity-40"
                  >
                    下移
                  </button>
                  <button
                    type="button"
                    onClick={() => onTest(p.id)}
                    disabled={busyTest !== null}
                    className="rounded border border-gray-200 px-2 py-0.5 text-xs text-gray-600 hover:bg-gray-50 disabled:opacity-40"
                  >
                    {busyTest === p.id ? '检测中…' : '检测'}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      if (window.confirm('确定删除该模型配置？')) onDelete(p.id);
                    }}
                    className="rounded border border-red-200 px-2 py-0.5 text-xs text-red-700 hover:bg-red-50"
                  >
                    删除
                  </button>
                </div>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
