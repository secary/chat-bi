import { useCallback, useEffect, useRef, useState } from 'react';
import {
  readMultiAgentsPreference,
  readSidebarOpenPreference,
  useChat,
  writeMultiAgentsPreference,
  writeSidebarOpenPreference,
} from '../hooks/useChat';
import { AssistantPendingNotice } from '../components/AssistantPendingNotice';
import { ChatComposerDock } from '../components/ChatComposerDock';
import { ChatSessionSidebar } from '../components/ChatSessionSidebar';
import { MessageBubble } from '../components/MessageBubble';
import { ChatWelcomeHero } from '../components/ChatWelcomeHero';
import { Switch } from '../components/Switch';
import { shouldShowChatWelcomeView } from '../lib/chatWelcomeView';
import {
  createSessionApi,
  deleteSessionApi,
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

export function ChatPage() {
  const bottomRef = useRef<HTMLDivElement>(null);
  const [sessions, setSessions] = useState<SessionRow[]>([]);
  const [suggestedPrompts, setSuggestedPrompts] = useState<string[]>([]);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [dbConnId, setDbConnId] = useState<number | null>(null);
  const [booting, setBooting] = useState(true);
  const [multiAgents, setMultiAgents] = useState(() => readMultiAgentsPreference());
  const [sidebarOpen, setSidebarOpen] = useState(() => readSidebarOpenPreference());
  const [pdfExporting, setPdfExporting] = useState(false);

  const { messages, loading, assistantPending, sendMessage, abort } = useChat(
    sessionId,
    dbConnId,
    multiAgents,
  );
  const inputBusy = loading || assistantPending;
  const showWelcome = shouldShowChatWelcomeView(booting, messages.length);

  useEffect(() => {
    writeMultiAgentsPreference(multiAgents);
  }, [multiAgents]);

  useEffect(() => {
    writeSidebarOpenPreference(sidebarOpen);
  }, [sidebarOpen]);

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
        setSessionId(resolveInitialSessionId(list, readLastSessionId()));
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
      <ChatSessionSidebar
        sidebarOpen={sidebarOpen}
        onSidebarOpenChange={setSidebarOpen}
        sessions={sessions}
        sessionId={sessionId}
        onSelectSession={setSessionId}
        onNewSession={newSession}
        onRemoveSession={removeSession}
      />

      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        <header className="flex flex-wrap items-center gap-3 border-b border-gray-200 bg-white/80 backdrop-blur-sm px-5 py-2.5">
          <div className="flex items-center gap-2 text-xs text-gray-600">
            <Switch
              id="multi-agents-switch"
              checked={multiAgents}
              onChange={setMultiAgents}
              disabled={booting}
              aria-label="多专线协作"
            />
            <label htmlFor="multi-agents-switch" className="cursor-pointer select-none">
              多专线协作
            </label>
          </div>
          <button
            type="button"
            disabled={booting || sessionId == null || pdfExporting}
            onClick={() => void exportPdf()}
            className="rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-xs text-gray-700 transition-colors hover:bg-gray-50 disabled:opacity-50"
          >
            {pdfExporting ? '导出中…' : '导出 PDF 报告'}
          </button>
          <label className="flex items-center gap-2 text-xs text-gray-600">
            数据源连接 ID（可选）
            <input
              type="number"
              className="w-24 rounded-lg border border-gray-200 px-2.5 py-1.5 text-xs transition-all focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
              placeholder="默认"
              value={dbConnId ?? ''}
              onChange={(e) =>
                setDbConnId(e.target.value === '' ? null : Number(e.target.value))
              }
            />
          </label>
        </header>

        {booting ? (
          <div className="flex flex-1 items-center justify-center px-6 py-6">
            <p className="text-center text-sm text-gray-400">加载会话…</p>
          </div>
        ) : showWelcome ? (
          <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
            <div className="flex min-h-0 flex-1 flex-col items-center justify-center overflow-y-auto px-6 py-8">
              <ChatWelcomeHero title="有什么可以帮到你？" subtitle="例如：1-4月销售额排行">
                <ChatComposerDock
                  suggestedPrompts={suggestedPrompts}
                  onSend={sendMessage}
                  onAbort={loading ? abort : undefined}
                  inputBusy={inputBusy}
                  booting={booting}
                  sessionId={sessionId}
                />
              </ChatWelcomeHero>
            </div>
          </div>
        ) : (
          <>
            <div className="flex-1 overflow-y-auto px-6 py-6">
              <div className="mx-auto max-w-3xl">
                {messages.map((msg) => (
                  <MessageBubble key={msg.id} message={msg} />
                ))}
                {assistantPending ? <AssistantPendingNotice /> : null}
                <div ref={bottomRef} />
              </div>
            </div>
            <div className="mx-auto w-full max-w-3xl px-4 pb-4">
              <ChatComposerDock
                suggestedPrompts={suggestedPrompts}
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
    </div>
  );
}
