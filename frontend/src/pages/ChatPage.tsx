import { useCallback, useEffect, useRef, useState } from 'react';
import { useChat } from '../hooks/useChat';
import { MessageBubble } from '../components/MessageBubble';
import { ChatInput } from '../components/ChatInput';
import {
  createSessionApi,
  deleteSessionApi,
  listSessionsApi,
} from '../api/client';
import type { SessionRow } from '../types/admin';
import { logger } from '../lib/logger';

export function ChatPage() {
  const bottomRef = useRef<HTMLDivElement>(null);
  const [sessions, setSessions] = useState<SessionRow[]>([]);
  const [suggestedPrompts, setSuggestedPrompts] = useState<string[]>([]);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [dbConnId, setDbConnId] = useState<number | null>(null);
  const [booting, setBooting] = useState(true);

  const { messages, loading, sendMessage } = useChat(sessionId, dbConnId);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const refreshSessions = useCallback(async () => {
    try {
      const data = await listSessionsApi();
      setSessions(data.sessions);
      setSuggestedPrompts(data.suggested_prompts);
      return data.sessions;
    } catch (e) {
      logger.error('list sessions', e);
      return [];
    }
  }, []);

  useEffect(() => {
    void (async () => {
      const list = await refreshSessions();
      if (list.length === 0) {
        try {
          const created = await createSessionApi();
          setSessionId(created.id);
          setSuggestedPrompts(created.suggested_prompts);
          await refreshSessions();
        } catch (e) {
          logger.error('create session', e);
        }
      } else {
        setSessionId(list[0].id);
      }
      setBooting(false);
    })();
  }, [refreshSessions]);

  const newSession = async () => {
    try {
      const created = await createSessionApi();
      setSessionId(created.id);
      setSuggestedPrompts(created.suggested_prompts);
      await refreshSessions();
    } catch (e) {
      logger.error('new session', e);
    }
  };

  const removeSession = async (id: number) => {
    try {
      await deleteSessionApi(id);
      const list = await refreshSessions();
      if (sessionId === id) {
        setSessionId(list[0]?.id ?? null);
        if (!list.length) {
          const created = await createSessionApi();
          setSessionId(created.id);
          setSuggestedPrompts(created.suggested_prompts);
          await refreshSessions();
        }
      }
    } catch (e) {
      logger.error('delete session', e);
    }
  };

  return (
    <div className="flex h-full">
      <aside className="flex w-56 shrink-0 flex-col border-r border-gray-200 bg-white">
        <div className="flex items-center justify-between border-b border-gray-100 px-3 py-2">
          <span className="text-xs font-medium text-gray-700">会话</span>
          <button
            type="button"
            onClick={() => void newSession()}
            className="rounded bg-gray-900 px-2 py-1 text-xs text-white hover:bg-gray-800"
          >
            新对话
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-2">
          {sessions.map((s) => (
            <div
              key={s.id}
              className={`group mb-1 flex items-center gap-1 rounded px-2 py-1.5 ${
                sessionId === s.id ? 'bg-gray-100' : 'hover:bg-gray-50'
              }`}
            >
              <button
                type="button"
                className="min-w-0 flex-1 truncate text-left text-xs text-gray-800"
                onClick={() => setSessionId(s.id)}
              >
                {s.title || `会话 ${s.id}`}
              </button>
              <button
                type="button"
                title="删除"
                className="shrink-0 text-xs text-gray-400 opacity-0 hover:text-red-600 group-hover:opacity-100"
                onClick={() => void removeSession(s.id)}
              >
                ×
              </button>
            </div>
          ))}
        </div>
      </aside>

      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        <header className="flex flex-wrap items-center gap-3 border-b border-gray-200 bg-white px-4 py-2">
          <label className="flex items-center gap-2 text-xs text-gray-600">
            数据源连接 ID（可选）
            <input
              type="number"
              className="w-24 rounded border border-gray-300 px-2 py-1 text-xs"
              placeholder="默认"
              value={dbConnId ?? ''}
              onChange={(e) =>
                setDbConnId(e.target.value === '' ? null : Number(e.target.value))
              }
            />
          </label>
        </header>

        <div className="flex-1 overflow-y-auto px-4 py-4">
          {booting ? (
            <p className="text-center text-sm text-gray-400">加载会话…</p>
          ) : (
            <div className="mx-auto max-w-3xl">
              {messages.length === 0 && (
                <div className="flex flex-col items-center justify-center pt-20 text-gray-400">
                  <p className="text-4xl mb-2">📊</p>
                  <p className="text-sm">输入业务问题开始分析</p>
                  <p className="mt-1 text-xs">例如：1-4月销售额排行</p>
                </div>
              )}
              {messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
              ))}
              <div ref={bottomRef} />
            </div>
          )}
        </div>

        <div className="mx-auto w-full max-w-3xl px-4 pb-4">
          {suggestedPrompts.length > 0 ? (
            <div className="mb-3 flex flex-wrap gap-2">
              <span className="w-full text-xs text-gray-500">记忆提示 · 可快捷继续：</span>
              {suggestedPrompts.map((p, idx) => (
                <button
                  key={`${idx}-${p.slice(0, 40)}`}
                  type="button"
                  onClick={() => void sendMessage(p)}
                  disabled={loading || booting || sessionId == null}
                  className="max-w-full truncate rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-left text-xs text-amber-900 hover:bg-amber-100 disabled:opacity-50"
                  title={p}
                >
                  {p}
                </button>
              ))}
            </div>
          ) : null}
          <ChatInput onSend={sendMessage} loading={loading} disabled={booting || sessionId == null} />
        </div>
      </div>
    </div>
  );
}
