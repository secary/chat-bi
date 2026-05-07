/** 与后端 CHATBI_AUTH_ENABLED 对齐：未设置时视为开启（生产构建）。 */
export function parseAuthEnabled(raw: string | undefined): boolean {
  if (raw === undefined || raw === '') return true;
  return !['0', 'false', 'no', 'off'].includes(String(raw).trim().toLowerCase());
}

export const authEnabled = parseAuthEnabled(import.meta.env.VITE_AUTH_ENABLED);
