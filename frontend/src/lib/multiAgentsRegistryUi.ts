/** UI helpers for Multi-Agent registry admin page（与后端专线 id 规则对齐） */

const SAFE_AGENT_ID = /^[a-zA-Z0-9][a-zA-Z0-9_-]{0,126}$/;

export function clampMaxAgentsRound(n: number): number {
  const v = Number.isFinite(n) ? Math.floor(Number(n)) : 2;
  return Math.min(8, Math.max(1, v));
}

export function isValidAgentId(id: string): boolean {
  const t = id.trim();
  if (!t || t.startsWith('_')) return false;
  return SAFE_AGENT_ID.test(t);
}
