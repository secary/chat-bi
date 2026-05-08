import type { SessionRow } from '../types/admin';

interface ChatSessionSidebarProps {
  sidebarOpen: boolean;
  onSidebarOpenChange: (open: boolean) => void;
  sessions: SessionRow[];
  sessionId: number | null;
  onSelectSession: (id: number) => void;
  onNewSession: () => void;
  onRemoveSession: (id: number) => void;
}

export function ChatSessionSidebar({
  sidebarOpen,
  onSidebarOpenChange,
  sessions,
  sessionId,
  onSelectSession,
  onNewSession,
  onRemoveSession,
}: ChatSessionSidebarProps) {
  return (
    <aside
      className={
        'flex shrink-0 flex-col border-r border-gray-200 bg-white transition-all duration-300 ' +
        (sidebarOpen ? 'w-56' : 'w-10')
      }
    >
      {sidebarOpen ? (
        <>
          <div className="flex items-center justify-between gap-1 border-b border-gray-100 px-3 py-2.5">
            <span className="text-xs font-medium tracking-wide text-gray-500">会话</span>
            <div className="flex shrink-0 items-center gap-1">
              <button
                type="button"
                title="收起会话列表"
                onClick={() => onSidebarOpenChange(false)}
                className="rounded-lg p-1.5 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
              >
                <span className="sr-only">收起会话列表</span>
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  aria-hidden
                >
                  <path d="M15 6l-6 6 6 6" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
              <button
                type="button"
                onClick={() => void onNewSession()}
                className="rounded-lg bg-gray-900 px-2.5 py-1 text-xs text-white transition-colors hover:bg-gray-800"
              >
                新对话
              </button>
            </div>
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-0.5">
            {sessions.map((s) => (
              <div
                key={s.id}
                className={`group flex items-center gap-1 rounded-lg px-2 py-1.5 transition-colors ${
                  sessionId === s.id ? 'bg-gray-100' : 'hover:bg-gray-50'
                }`}
              >
                <button
                  type="button"
                  className="min-w-0 flex-1 truncate text-left text-xs text-gray-700"
                  onClick={() => onSelectSession(s.id)}
                >
                  {s.title || `会话 ${s.id}`}
                </button>
                <button
                  type="button"
                  title="删除"
                  className="shrink-0 text-xs text-gray-400 opacity-0 transition-opacity hover:text-red-500 group-hover:opacity-100"
                  onClick={() => void onRemoveSession(s.id)}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        </>
      ) : (
        <div className="flex flex-1 flex-col items-center gap-3 py-3">
          <button
            type="button"
            title="展开会话列表"
            onClick={() => onSidebarOpenChange(true)}
            className="rounded-lg p-1.5 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
          >
            <span className="sr-only">展开会话列表</span>
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              aria-hidden
            >
              <path d="M9 6l6 6-6 6" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </div>
      )}
    </aside>
  );
}
