import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useChat } from '../hooks/useChat';
import { AssistantPendingNotice } from '../components/AssistantPendingNotice';
import { ChatComposerDock } from '../components/ChatComposerDock';
import { MessageBubble } from '../components/MessageBubble';
import { ChatWelcomeHero } from '../components/ChatWelcomeHero';
import { shouldShowChatWelcomeView } from '../lib/chatWelcomeView';
import {
  createSessionApi,
  downloadSessionReportPdf,
  listSessionsApi,
} from '../api/client';
import type { SessionRow } from '../types/admin';
import { logger } from '../lib/logger';
import {
  readLastSessionId,
  resolveInitialSessionId,
  writeLastSessionId,
} from '../lib/sessionSelection';
import { useAuth } from '../contexts/useAuth';

export function ChatPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const bottomRef = useRef<HTMLDivElement>(null);
  const [sessions, setSessions] = useState<SessionRow[]>([]);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [dbConnId, setDbConnId] = useState<number | null>(null);
  const [booting, setBooting] = useState(true);
  const [pdfExporting, setPdfExporting] = useState(false);

  const { messages, loading, assistantPending, currentTraceId, lastTraceId, sendMessage, abort } =
    useChat(sessionId, dbConnId);
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

  const newSession = async () => {
    try {
      const created = await createSessionApi();
      setSessionId(created.id);
      await refreshSessions();
    } catch (e) {
      logger.error('new session', e);
    }
  };

  const exportPdf = async () => {
    if (sessionId == null || pdfExporting) return;
    setPdfExporting(true);
    try {
      const blob = await downloadSessionReportPdf(sessionId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `chatbi-session-${sessionId}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      logger.error('export pdf', e);
    } finally {
      setPdfExporting(false);
    }
  };

  return (
    <div className="flex h-full min-h-0 min-w-0 flex-col bg-white">
      <header className="flex flex-wrap items-center gap-3 border-b border-gray-100 bg-white px-6 py-3">
        <button
          type="button"
          disabled={booting}
          onClick={() => void newSession()}
          className="rounded-full bg-gray-900 px-3.5 py-1.5 text-xs font-medium text-white transition-colors hover:bg-gray-800 disabled:opacity-50"
        >
          新对话
        </button>
        <button
          type="button"
          disabled={booting || sessionId == null || pdfExporting}
          onClick={() => void exportPdf()}
          className="rounded-full border border-gray-200 bg-white px-3.5 py-1.5 text-xs text-gray-700 transition-colors hover:bg-gray-50 disabled:opacity-50"
        >
          {pdfExporting ? '导出中…' : '导出 PDF 报告'}
        </button>
        <label className="flex items-center gap-2 text-xs text-gray-600">
          数据源连接 ID（可选）
          <input
            type="number"
            className="w-24 rounded-full border border-gray-200 px-3 py-1.5 text-xs transition-all focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30"
            placeholder="默认"
            value={dbConnId ?? ''}
            onChange={(e) => setDbConnId(e.target.value === '' ? null : Number(e.target.value))}
          />
        </label>
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
                onSend={sendMessage}
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
              onSend={sendMessage}
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
