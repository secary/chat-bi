import { useCallback, useEffect, useRef, useState } from 'react';
import type { ChatMessage } from '../types/message';
import { getSessionMessagesApi, streamChat } from '../api/client';
import { logger } from '../lib/logger';

let nextId = 1;

function mapRow(row: Record<string, unknown>): ChatMessage {
  return {
    id: String(row.id),
    role: row.role as ChatMessage['role'],
    content: String(row.content ?? ''),
    thinking: row.thinking as string[] | undefined,
    chart: row.chart as Record<string, unknown> | undefined,
    kpiCards: row.kpiCards as ChatMessage['kpiCards'],
    error: row.error as string | undefined,
  };
}

export interface UseChatReturn {
  messages: ChatMessage[];
  loading: boolean;
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

  return { messages, loading, sendMessage };
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
