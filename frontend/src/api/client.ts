import type { ChatRequest, SseEvent, UploadedFile } from '../types/message';
import type {
  AdminSkillRow,
  CurrentDbConnectionView,
  DbConnectionRow,
  LlmSettingsView,
  MultiAgentsRegistryPayload,
  SessionListApi,
} from '../types/admin';
import type { AppUser, AppUserRow } from '../types/auth';
import type { DashboardOverview } from '../types/dashboard';
import { authEnabled } from '../lib/authFlags';

export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');
const CHAT_URL = `${API_BASE_URL}/chat`;
const UPLOAD_URL = `${API_BASE_URL}/upload`;
const TOKEN_KEY = 'chatbi_token';

export function getStoredToken(): string | null {
  try {
    return sessionStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setStoredToken(token: string | null): void {
  try {
    if (token) sessionStorage.setItem(TOKEN_KEY, token);
    else sessionStorage.removeItem(TOKEN_KEY);
  } catch {
    /* ignore */
  }
}

function authHeaders(extra?: Record<string, string>): Record<string, string> {
  const h: Record<string, string> = { ...(extra || {}) };
  const t = getStoredToken();
  if (t) h.Authorization = `Bearer ${t}`;
  return h;
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = authHeaders(
    init?.headers as Record<string, string> | undefined,
  );
  if (init?.body && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }
  const res = await fetch(`${API_BASE_URL}${path}`, { ...init, headers });
  if (
    authEnabled &&
    res.status === 401 &&
    !path.startsWith('/auth/login')
  ) {
    setStoredToken(null);
    if (typeof window !== 'undefined' && !window.location.pathname.endsWith('/login')) {
      window.location.assign('/login');
    }
  }
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `请求失败: ${res.status}`);
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return res.json() as Promise<T>;
}

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
    headers: authHeaders({
      'Content-Type': 'application/json',
      'X-Trace-Id': traceId,
    }),
    body: JSON.stringify(req),
  });

  if (response.status === 401) {
    if (authEnabled) {
      setStoredToken(null);
      if (typeof window !== 'undefined' && !window.location.pathname.endsWith('/login')) {
        window.location.assign('/login');
      }
    }
    yield { type: 'error', content: '未登录或会话已过期' };
    return;
  }

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
    headers: authHeaders({ 'X-Trace-Id': traceId }),
    body: formData,
  });

  if (response.status === 401) {
    if (authEnabled) {
      setStoredToken(null);
      if (typeof window !== 'undefined' && !window.location.pathname.endsWith('/login')) {
        window.location.assign('/login');
      }
    }
    throw new Error('未登录或会话已过期');
  }

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

export async function getDashboardOverview(): Promise<DashboardOverview> {
  return requestJson<DashboardOverview>('/dashboard/overview');
}

export async function listSessionsApi(): Promise<SessionListApi> {
  return requestJson<SessionListApi>('/sessions');
}

export async function createSessionApi(
  title = '新对话',
): Promise<{ id: number; suggested_prompts: string[] }> {
  return requestJson<{ id: number; suggested_prompts: string[] }>('/sessions', {
    method: 'POST',
    body: JSON.stringify({ title }),
  });
}

export async function loginApi(username: string, password: string): Promise<string> {
  const res = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || '登录失败');
  }
  const data = (await res.json()) as { access_token: string };
  return data.access_token;
}

export async function getMeApi(): Promise<AppUser> {
  return requestJson<AppUser>('/auth/me');
}

export async function listUsersApi(): Promise<AppUserRow[]> {
  return requestJson<AppUserRow[]>('/admin/users');
}

export async function createUserApi(payload: {
  username: string;
  password: string;
  role: string;
}): Promise<{ id: number }> {
  return requestJson<{ id: number }>('/admin/users', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function patchUserApi(
  id: number,
  payload: { password?: string; role?: string; is_active?: boolean },
): Promise<void> {
  await requestJson(`/admin/users/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export async function deactivateUserApi(id: number): Promise<void> {
  await requestJson(`/admin/users/${id}`, { method: 'DELETE' });
}

export async function deleteSessionApi(id: number): Promise<void> {
  await requestJson(`/sessions/${id}`, { method: 'DELETE' });
}

export async function getSessionMessagesApi(
  id: number,
): Promise<Record<string, unknown>[]> {
  return requestJson<Record<string, unknown>[]>(`/sessions/${id}/messages`);
}

export async function downloadSessionReportPdf(sessionId: number): Promise<Blob> {
  const res = await fetch(`${API_BASE_URL}/sessions/${sessionId}/report.pdf`, {
    headers: authHeaders(),
  });
  if (
    authEnabled &&
    res.status === 401 &&
    typeof window !== 'undefined' &&
    !window.location.pathname.endsWith('/login')
  ) {
    setStoredToken(null);
    window.location.assign('/login');
  }
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `导出失败: ${res.status}`);
  }
  return res.blob();
}

export async function listAdminSkills(): Promise<AdminSkillRow[]> {
  return requestJson<AdminSkillRow[]>('/admin/skills');
}

export async function getMultiAgentsRegistry(): Promise<MultiAgentsRegistryPayload> {
  return requestJson<MultiAgentsRegistryPayload>('/admin/multi-agents');
}

export async function putMultiAgentsRegistry(
  payload: MultiAgentsRegistryPayload,
): Promise<MultiAgentsRegistryPayload> {
  return requestJson<MultiAgentsRegistryPayload>('/admin/multi-agents', {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export async function getSkillFile(slug: string): Promise<{ markdown: string }> {
  return requestJson<{ markdown: string }>(`/admin/skills/${encodeURIComponent(slug)}/file`);
}

export async function putSkillFile(slug: string, markdown: string): Promise<void> {
  await requestJson(`/admin/skills/${encodeURIComponent(slug)}`, {
    method: 'PUT',
    body: JSON.stringify({ markdown }),
  });
}

export async function patchSkillEnabled(slug: string, enabled: boolean): Promise<void> {
  await requestJson(`/admin/skills/${encodeURIComponent(slug)}`, {
    method: 'PATCH',
    body: JSON.stringify({ enabled }),
  });
}

export async function createSkillApi(slug: string, markdown = ''): Promise<void> {
  await requestJson('/admin/skills', {
    method: 'POST',
    body: JSON.stringify({ slug, markdown }),
  });
}

export async function deleteSkillApi(slug: string): Promise<void> {
  await requestJson(`/admin/skills/${encodeURIComponent(slug)}`, { method: 'DELETE' });
}

export async function listDbConnections(): Promise<DbConnectionRow[]> {
  return requestJson<DbConnectionRow[]>('/admin/db-connections');
}

export async function getCurrentDbConnection(): Promise<CurrentDbConnectionView> {
  return requestJson<CurrentDbConnectionView>('/admin/db-connections/current');
}

export async function createDbConnectionApi(payload: {
  name: string;
  host: string;
  port: number;
  username: string;
  password: string;
  database_name: string;
  is_default: boolean;
}): Promise<void> {
  await requestJson('/admin/db-connections', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updateDbConnectionApi(
  id: number,
  payload: {
    name: string;
    host: string;
    port: number;
    username: string;
    password?: string | null;
    database_name: string;
    is_default: boolean;
  },
): Promise<void> {
  await requestJson(`/admin/db-connections/${id}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export async function deleteDbConnectionApi(id: number): Promise<void> {
  await requestJson(`/admin/db-connections/${id}`, { method: 'DELETE' });
}

export async function testDbConnectionApi(id: number): Promise<void> {
  await requestJson(`/admin/db-connections/${id}/test`, { method: 'POST' });
}

export async function getLlmSettings(): Promise<LlmSettingsView> {
  return requestJson<LlmSettingsView>('/admin/llm-settings');
}

export async function putLlmSettings(payload: {
  model?: string | null;
  api_base?: string | null;
  api_key?: string | null;
}): Promise<LlmSettingsView> {
  return requestJson<LlmSettingsView>('/admin/llm-settings', {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}
