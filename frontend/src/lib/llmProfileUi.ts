/** Pure helpers for LLM profile list presentation. */

export function profileListTitle(displayName: string | null | undefined, model: string): string {
  const d = displayName?.trim();
  return d || model;
}

export function healthStatusLabel(status: string): string {
  if (status === 'ok') return '可用';
  if (status === 'error') return '不可用';
  return '未检测';
}
