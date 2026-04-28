import { useCallback, useRef, useState } from 'react';
import type { ChatMessage, SseEvent } from '../types/message';
import { streamChat } from '../api/client';

export interface UseChatReturn {
  messages: ChatMessage[];
  loading: boolean;
  sendMessage: (text: string) => Promise<void>;
  clearMessages: () => void;
}

let nextId = 1;

export function useChat(): UseChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const messagesRef = useRef(messages);
  messagesRef.current = messages;

  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim() || loading) return;

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
      for await (const event of streamChat({ message: text, history })) {
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
      setMessages((prev) => {
        const updated = [...prev];
        const last = updated[updated.length - 1];
        if (last?.role === 'assistant') last.error = String(err);
        return updated;
      });
    } finally {
      setLoading(false);
    }
  }, [loading]);

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  return { messages, loading, sendMessage, clearMessages };
}
