import { useCallback, useEffect, useRef, useState } from 'react';
import type { ChatMessage } from '../types/message';
import { getSessionMessagesApi, streamChat } from '../api/client';
import { isWaitingForAssistantMessage } from '../lib/chatPending';
import { logger } from '../lib/logger';

let nextId = 1;

const POLL_PENDING_MS = 1000;
/** ~3 minutes at 1s interval */
const POLL_PENDING_MAX_ATTEMPTS = 180;

function mapRow(row: Record<string, unknown>): ChatMessage {
  return {
    id: String(row.id),
    role: row.role as ChatMessage['role'],
    content: String(row.content ?? ''),
    thinking: row.thinking as string[] | undefined,
    chart: row.chart as Record<string, unknown> | undefined,
    kpiCards: row.kpiCards as ChatMessage['kpiCards'],
    planSummary: row.planSummary as ChatMessage['planSummary'],
    error: row.error as string | undefined,
  };
}

export interface UseChatReturn {
  messages: ChatMessage[];
  loading: boolean;
  /** Last loaded message is user — assistant row not yet in DB (e.g. navigated away mid-stream). */
  assistantPending: boolean;
  sendMessage: (text: string, traceId?: string) => Promise<void>;
}

const MULTI_AGENTS_KEY = 'chatbi_multi_agents';

export function useChat(
  sessionId: number | null,
  dbConnectionId: number | null,
  multiAgents: boolean,
): UseChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const messagesRef = useRef(messages);
  const streamingRef = useRef(false);

  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  useEffect(() => {
    if (sessionId == null) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- clear when session cleared
      setMessages([]);
      return;
    }
    let cancelled = false;
    void getSessionMessagesApi(sessionId)
      .then((rows) => {
        if (cancelled) return;
        const maxId = rows.reduce(
          (m, r) => Math.max(m, Number(r.id) || 0),
          0,
        );
        nextId = maxId + 1;
        setMessages(rows.map(mapRow));
      })
      .catch((err: unknown) => {
        logger.error('load messages', err);
      });
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  const assistantPending = isWaitingForAssistantMessage(sessionId, messages);

  useEffect(() => {
    if (!assistantPending || sessionId == null) return;

    const sid = sessionId;
    let cancelled = false;
    let attempts = 0;
    let intervalId = 0;

    const finishIfAssistant = (rows: Record<string, unknown>[]): boolean => {
      const lastRow = rows[rows.length - 1];
      return Boolean(lastRow && String(lastRow.role) === 'assistant');
    };

    const tick = async () => {
      if (cancelled) return;
      attempts += 1;
      if (attempts > POLL_PENDING_MAX_ATTEMPTS) {
        window.clearInterval(intervalId);
        return;
      }
      try {
        const rows = await getSessionMessagesApi(sid);
        if (cancelled) return;
        const maxId = rows.reduce(
          (m, r) => Math.max(m, Number(r.id) || 0),
          0,
        );
        nextId = maxId + 1;
        setMessages(rows.map(mapRow));
        if (finishIfAssistant(rows)) {
          window.clearInterval(intervalId);
        }
      } catch (err: unknown) {
        logger.error('poll session messages', err);
      }
    };

    intervalId = window.setInterval(() => void tick(), POLL_PENDING_MS);
    void tick();

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [sessionId, assistantPending]);

  const sendMessage = useCallback(
    async (text: string, traceId?: string) => {
      if (!text.trim() || loading || streamingRef.current || sessionId == null) {
        return;
      }
      streamingRef.current = true;

      const userMsg: ChatMessage = {
        id: String(nextId++),
        role: 'user',
        content: text,
      };
      const assistantMsg: ChatMessage = {
        id: String(nextId++),
        role: 'assistant',
        content: '',
        thinking: [],
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setLoading(true);

      const history =
        sessionId != null
          ? []
          : messagesRef.current.slice(-10).map((m) => ({
              role: m.role,
              content: m.content,
            }));

      try {
        for await (const event of streamChat(
          {
            message: text,
            history,
            session_id: sessionId,
            db_connection_id: dbConnectionId ?? undefined,
            multi_agents: multiAgents,
          },
          traceId,
        )) {
          setMessages((prev) => {
            const idx = prev.length - 1;
            const last = prev[idx];
            if (!last || last.role !== 'assistant') return prev;

            const nextLast: ChatMessage = { ...last };
            switch (event.type) {
              case 'thinking':
                nextLast.thinking = [...(last.thinking || []), String(event.content)];
                break;
              case 'text':
                nextLast.content = last.content
                  ? `${last.content}\n\n${String(event.content)}`
                  : String(event.content);
                break;
              case 'chart':
                nextLast.chart = event.content as Record<string, unknown>;
                break;
              case 'kpi_cards':
                nextLast.kpiCards = event.content as typeof last.kpiCards;
                break;
              case 'plan_summary':
                nextLast.planSummary = event.content as ChatMessage['planSummary'];
                break;
              case 'error':
                nextLast.error = String(event.content);
                break;
              default:
                return prev;
            }

            return [...prev.slice(0, idx), nextLast];
          });
        }
      } catch (err) {
        logger.error('stream chat', err);
        setMessages((prev) => {
          const idx = prev.length - 1;
          const last = prev[idx];
          if (!last || last.role !== 'assistant') return prev;
          const nextLast: ChatMessage = { ...last, error: String(err) };
          return [...prev.slice(0, idx), nextLast];
        });
      } finally {
        streamingRef.current = false;
        setLoading(false);
      }
    },
    [loading, sessionId, dbConnectionId, multiAgents],
  );

  return { messages, loading, assistantPending, sendMessage };
}

export function readMultiAgentsPreference(): boolean {
  try {
    return localStorage.getItem(MULTI_AGENTS_KEY) === '1';
  } catch {
    return false;
  }
}

export function writeMultiAgentsPreference(value: boolean): void {
  try {
    localStorage.setItem(MULTI_AGENTS_KEY, value ? '1' : '0');
  } catch {
    /* ignore */
  }
}

const SIDEBAR_OPEN_KEY = 'chatbi_sidebar_open';

export function readSidebarOpenPreference(): boolean {
  try {
    const v = localStorage.getItem(SIDEBAR_OPEN_KEY);
    if (v === null) return true;
    return v === '1';
  } catch {
    return true;
  }
}

export function writeSidebarOpenPreference(value: boolean): void {
  try {
    localStorage.setItem(SIDEBAR_OPEN_KEY, value ? '1' : '0');
  } catch {
    /* ignore */
  }
}
