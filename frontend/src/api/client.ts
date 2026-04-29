import type { ChatRequest, SseEvent, UploadedFile } from '../types/message';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');
const CHAT_URL = `${API_BASE_URL}/chat`;
const UPLOAD_URL = `${API_BASE_URL}/upload`;

export function parseSseLine(line: string): SseEvent | null {
  if (!line.startsWith('data: ')) return null;
  try {
    return JSON.parse(line.slice(6)) as SseEvent;
  } catch {
    return null;
  }
}

export function newTraceId(): string {
  if (crypto.randomUUID) return crypto.randomUUID().replaceAll('-', '');
  return `${Date.now().toString(36)}${Math.random().toString(36).slice(2)}`;
}

export async function* streamChat(
  req: ChatRequest,
  traceId = newTraceId(),
): AsyncGenerator<SseEvent> {
  const response = await fetch(CHAT_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Trace-Id': traceId },
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

export async function uploadFile(file: File, traceId = newTraceId()): Promise<UploadedFile> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(UPLOAD_URL, {
    method: 'POST',
    headers: { 'X-Trace-Id': traceId },
    body: formData,
  });

  if (!response.ok) {
    let detail = `上传失败: ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      // Keep the status-based fallback.
    }
    throw new Error(detail);
  }

  return (await response.json()) as UploadedFile;
}
