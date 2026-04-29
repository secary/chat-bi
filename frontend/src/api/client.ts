import type { ChatRequest, SseEvent } from '../types/message';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');
const CHAT_URL = `${API_BASE_URL}/chat`;

export function parseSseLine(line: string): SseEvent | null {
  if (!line.startsWith('data: ')) return null;
  try {
    return JSON.parse(line.slice(6)) as SseEvent;
  } catch {
    return null;
  }
}

export async function* streamChat(req: ChatRequest): AsyncGenerator<SseEvent> {
  const response = await fetch(CHAT_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });

  if (!response.ok) {
    yield { type: 'error', content: `请求失败: ${response.status}` };
    return;
  }

  const reader = response.body?.getReader();
  if (!reader) {
    yield { type: 'error', content: '无法读取响应流' };
    return;
  }

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('event: message')) continue;
      const event = parseSseLine(line);
      if (event) yield event;
    }
  }

  // Process remaining buffer
  if (buffer.trim()) {
    const event = parseSseLine(buffer.trim());
    if (event) yield event;
  }
}
