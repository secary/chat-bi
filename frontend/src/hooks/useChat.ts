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

export function useChat(
  sessionId: number | null,
  dbConnectionId: number | null,
): UseChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const messagesRef = useRef(messages);

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
      if (!text.trim() || loading || sessionId == null) return;

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
          },
          traceId,
        )) {
          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last?.role !== 'assistant') return updated;

            switch (event.type) {
              case 'thinking': {
                last.thinking = [...(last.thinking || []), String(event.content)];
                break;
              }
              case 'text': {
                last.content += String(event.content);
                break;
              }
              case 'chart': {
                last.chart = event.content as Record<string, unknown>;
                break;
              }
              case 'kpi_cards': {
                last.kpiCards = event.content as typeof last.kpiCards;
                break;
              }
              case 'error': {
                last.error = String(event.content);
                break;
              }
            }
            return updated;
          });
        }
      } catch (err) {
        logger.error('stream chat', err);
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last?.role === 'assistant') last.error = String(err);
          return updated;
        });
      } finally {
        setLoading(false);
      }
    },
    [loading, sessionId, dbConnectionId],
  );

  return { messages, loading, sendMessage };
}
