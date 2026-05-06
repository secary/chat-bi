import { useCallback, useEffect, useRef, useState } from 'react';
import type { ChatMessage } from '../types/message';
import { streamChat } from '../api/client';

export interface UseChatReturn {
  messages: ChatMessage[];
  loading: boolean;
  sendMessage: (text: string, traceId?: string) => Promise<void>;
  clearMessages: () => void;
}

let nextId = 1;

export function useChat(): UseChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const messagesRef = useRef(messages);
  const streamingRef = useRef(false);

  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  const sendMessage = useCallback(async (text: string, traceId?: string) => {
    if (!text.trim() || loading || streamingRef.current) return;
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

    const history = messagesRef.current.slice(-10).map((m) => ({
      role: m.role,
      content: m.content,
    }));

    try {
      for await (const event of streamChat({ message: text, history }, traceId)) {
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last?.role !== 'assistant') return updated;

          switch (event.type) {
            case 'thinking': {
              updated[updated.length - 1] = {
                ...last,
                thinking: [...(last.thinking || []), String(event.content)],
              };
              break;
            }
            case 'text': {
              const nextChunk = String(event.content);
              updated[updated.length - 1] = {
                ...last,
                content: last.content ? `${last.content}\n\n${nextChunk}` : nextChunk,
              };
              break;
            }
            case 'chart': {
              updated[updated.length - 1] = { ...last, chart: event.content as Record<string, unknown> };
              break;
            }
            case 'kpi_cards': {
              updated[updated.length - 1] = { ...last, kpiCards: event.content as typeof last.kpiCards };
              break;
            }
            case 'error': {
              updated[updated.length - 1] = { ...last, error: String(event.content) };
              break;
            }
          }
          return updated;
        });
      }
    } catch (err) {
      setMessages((prev) => {
        const updated = [...prev];
        const last = updated[updated.length - 1];
        if (last?.role === 'assistant') last.error = String(err);
        return updated;
      });
    } finally {
      streamingRef.current = false;
      setLoading(false);
    }
  }, [loading]);

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  return { messages, loading, sendMessage, clearMessages };
}
