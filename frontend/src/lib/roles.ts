export function isAdminRole(role: string | null | undefined): boolean {
  return role === 'root' || role === 'admin';
}
