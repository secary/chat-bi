/** Persist last chat session so SPA navigation does not reset selection to list[0]. */

const LAST_SESSION_KEY = 'chatbi_last_session_id';

export function readLastSessionId(): number | null {
  try {
    const v = sessionStorage.getItem(LAST_SESSION_KEY);
    if (!v) return null;
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
  } catch {
    return null;
  }
}

export function writeLastSessionId(id: number | null): void {
  try {
    if (id == null) sessionStorage.removeItem(LAST_SESSION_KEY);
    else sessionStorage.setItem(LAST_SESSION_KEY, String(id));
  } catch {
    /* ignore */
  }
}

/**
 * Prefer stored id when it still exists; otherwise most recently updated session (list order).
 */
export function resolveInitialSessionId(
  sessions: readonly { id: number }[],
  stored: number | null,
): number {
  if (sessions.length === 0) {
    throw new Error('resolveInitialSessionId requires a non-empty session list');
  }
  if (stored != null && sessions.some((s) => s.id === stored)) {
    return stored;
  }
  return sessions[0].id;
}
