import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useChat } from '../hooks/useChat';
import { AssistantPendingNotice } from '../components/AssistantPendingNotice';
import { ChatComposerDock } from '../components/ChatComposerDock';
import { MessageBubble } from '../components/MessageBubble';
import { ChatWelcomeHero } from '../components/ChatWelcomeHero';
import { shouldShowChatWelcomeView } from '../lib/chatWelcomeView';
import { createSessionApi, listDbConnections, listSessionsApi } from '../api/client';
import type { DbConnectionRow, SessionRow } from '../types/admin';
import { logger } from '../lib/logger';
import {
  readLastSessionId,
  resolveInitialSessionId,
  writeLastSessionId,
} from '../lib/sessionSelection';
import { useAuth } from '../contexts/useAuth';
import { resolveDataSourceSwitch } from '../lib/dataSourceSwitch';

export function ChatPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const bottomRef = useRef<HTMLDivElement>(null);
  const [sessions, setSessions] = useState<SessionRow[]>([]);
  const [dbConnections, setDbConnections] = useState<DbConnectionRow[]>([]);
  const [dbConnectionId, setDbConnectionId] = useState<number | null>(null);
  const [dataSourceNotice, setDataSourceNotice] = useState('');
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [booting, setBooting] = useState(true);

  const { messages, loading, assistantPending, currentTraceId, lastTraceId, sendMessage, abort } =
    useChat(sessionId, dbConnectionId);
  const inputBusy = loading || assistantPending;
  const showWelcome = shouldShowChatWelcomeView(booting, messages.length);
  const inspectableTraceId = currentTraceId || lastTraceId;

  useEffect(() => {
    if (sessionId != null) writeLastSessionId(sessionId);
  }, [sessionId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, assistantPending]);

  const refreshSessions = useCallback(async () => {
    try {
      const data = await listSessionsApi();
      setSessions(data.sessions);
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
          await refreshSessions();
        } catch (e) {
          logger.error('create session', e);
        }
      } else {
        setSessionId(resolveInitialSessionId(list, readLastSessionId()));
      }
      setBooting(false);
    })();
  }, [refreshSessions]);

  useEffect(() => {
    if (user?.role !== 'admin') return;
    void listDbConnections()
      .then((rows) => {
        setDbConnections(rows);
        const defaultRow = rows.find((item) => item.is_default);
        setDbConnectionId(defaultRow?.id ?? null);
      })
      .catch((e: unknown) => {
        logger.error('list db connections for chat', e);
      });
  }, [user?.role]);

  const newSession = async () => {
    try {
      const created = await createSessionApi();
      setSessionId(created.id);
      await refreshSessions();
    } catch (e) {
      logger.error('new session', e);
    }
  };

  const sendWithDataSourceSwitch = useCallback(
    async (text: string, traceId?: string, uploads?: Parameters<typeof sendMessage>[2]) => {
      const match = resolveDataSourceSwitch(text, dbConnections);
      if (match.status === 'unique') {
        setDbConnectionId(match.row.id);
        setDataSourceNotice(`已切换到数据源：${match.row.name}`);
        await sendMessage(text, traceId, uploads, match.row.id);
        return;
      }
      if (match.status === 'ambiguous') {
        setDataSourceNotice(
          `检测到多个可能的数据源：${match.rows.map((row) => row.name).join('、')}，请先手动选择。`,
        );
        await sendMessage(text, traceId, uploads);
        return;
      }
      setDataSourceNotice('');
      await sendMessage(text, traceId, uploads);
    },
    [dbConnections, sendMessage],
  );

  return (
    <div className="flex h-full min-h-0 min-w-0 flex-col bg-white">
      <header className="flex flex-wrap items-center gap-3 border-b border-gray-100 bg-white px-6 py-3">
        <button
          type="button"
          disabled={booting}
          onClick={() => void newSession()}
          className="rounded-full bg-accent px-3.5 py-1.5 text-xs font-medium text-white transition-colors hover:bg-accent-hover disabled:opacity-50"
        >
          新对话
        </button>
        {user?.role === 'admin' ? (
          <label className="flex items-center gap-2 text-xs text-gray-500">
            <span>数据源</span>
            <select
              value={dbConnectionId ?? ''}
              onChange={(e) => {
                const value = Number(e.target.value);
                setDbConnectionId(Number.isFinite(value) && value > 0 ? value : null);
                setDataSourceNotice('');
              }}
              className="h-8 min-w-48 rounded-lg border border-gray-200 bg-white px-2 text-xs text-gray-700 outline-none transition-colors focus:border-accent"
            >
              <option value="">默认连接</option>
              {dbConnections.map((row) => (
                <option key={row.id} value={row.id}>
                  {row.name}
                  {row.is_default ? '（默认）' : ''}
                </option>
              ))}
            </select>
          </label>
        ) : null}
        {user?.role === 'admin' && inspectableTraceId ? (
          <div className="ml-auto flex items-center gap-2 rounded-lg border border-gray-200 bg-gray-50 px-2.5 py-1.5 text-xs text-gray-600">
            <span className="text-gray-400">{currentTraceId ? '当前 trace' : '最近 trace'}</span>
            <button
              type="button"
              className="max-w-[260px] truncate font-mono text-gray-800 transition-colors hover:text-accent"
              title={inspectableTraceId}
              onClick={() => navigate(`/audits?trace_id=${encodeURIComponent(inspectableTraceId)}`)}
            >
              {inspectableTraceId}
            </button>
            <button
              type="button"
              className="rounded-md border border-gray-200 bg-white px-2 py-0.5 text-[11px] text-gray-700 transition-colors hover:bg-gray-100"
              onClick={() => navigate(`/audits?trace_id=${encodeURIComponent(inspectableTraceId)}`)}
            >
              去审计
            </button>
          </div>
        ) : null}
      </header>
      {dataSourceNotice ? (
        <div className="border-b border-emerald-100 bg-emerald-50 px-6 py-2 text-xs text-emerald-800">
          {dataSourceNotice}
        </div>
      ) : null}

      {booting ? (
        <div className="flex flex-1 items-center justify-center px-6 py-6">
          <p className="text-center text-sm text-gray-400">加载会话…</p>
        </div>
      ) : showWelcome ? (
        <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
          <div className="flex min-h-0 flex-1 flex-col items-center overflow-y-auto px-7 py-10">
            <ChatWelcomeHero
              title="把问题变成"
              sessions={sessions}
              onSelectSession={setSessionId}
            >
              <ChatComposerDock
                onSend={sendWithDataSourceSwitch}
                onAbort={loading ? abort : undefined}
                inputBusy={inputBusy}
                booting={booting}
                sessionId={sessionId}
                variant="welcome"
              />
            </ChatWelcomeHero>
          </div>
        </div>
      ) : (
        <>
          <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-y-auto px-6 py-6">
            <div className="mx-auto min-w-0 w-full max-w-3xl">
              {messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
              ))}
              {assistantPending ? <AssistantPendingNotice /> : null}
              <div ref={bottomRef} />
            </div>
          </div>
          <div className="mx-auto min-w-0 w-full max-w-3xl px-4 pb-4">
            <ChatComposerDock
              onSend={sendWithDataSourceSwitch}
              onAbort={loading ? abort : undefined}
              inputBusy={inputBusy}
              booting={booting}
              sessionId={sessionId}
            />
          </div>
        </>
      )}
    </div>
  );
}
