import type { AppUserRow } from '../types/auth';

type UserRole = 'admin' | 'user';

type UserAdminTableProps = {
  rows: AppUserRow[];
  loading: boolean;
  busyId: number | null;
  currentUserId: number;
  currentUsername: string;
  onRoleChange: (row: AppUserRow, role: UserRole) => void;
  onResetPassword: (row: AppUserRow) => void;
  onToggleActive: (row: AppUserRow) => void;
  isActive: (row: AppUserRow) => boolean;
};

export function UserAdminTable({
  rows,
  loading,
  busyId,
  currentUserId,
  currentUsername,
  onRoleChange,
  onResetPassword,
  onToggleActive,
  isActive,
}: UserAdminTableProps) {
  return (
    <div className="min-w-0 overflow-hidden rounded-lg border border-gray-200 bg-white shadow-card">
      <div className="flex items-center justify-between gap-3 border-b border-gray-100 px-4 py-3">
        <h2 className="text-sm font-semibold text-gray-900">账号列表</h2>
        <span className="text-xs text-gray-400">{loading ? '读取中' : `${rows.length} 个账号`}</span>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-gray-50 text-xs font-medium text-gray-500">
            <tr>
              <th className="px-4 py-3">账号</th>
              <th className="px-4 py-3">角色</th>
              <th className="px-4 py-3">状态</th>
              <th className="px-4 py-3">创建时间</th>
              <th className="px-4 py-3 text-right">操作</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              <tr>
                <td colSpan={5} className="px-4 py-10 text-center text-gray-400">
                  加载中…
                </td>
              </tr>
            ) : rows.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-10 text-center text-gray-400">
                  暂无用户
                </td>
              </tr>
            ) : (
              rows.map((row) => {
                const active = isActive(row);
                const self = row.id === currentUserId;
                const rootRow = row.username === 'root';
                const adminRow = row.role === 'admin';
                const currentUserIsRoot = currentUsername === 'root';
                const busy = busyId === row.id;
                const canManageRole = currentUserIsRoot && !rootRow;
                const canResetPassword = !busy && (!adminRow || currentUserIsRoot || self) && (!rootRow || self);
                const canToggleActive = !busy && !rootRow && !(self && active) && (!adminRow || currentUserIsRoot);
                return (
                  <tr key={row.id} className="transition-colors hover:bg-gray-50/70">
                    <td className="px-4 py-3">
                      <div className="flex min-w-0 items-center gap-2">
                        <span className="truncate font-medium text-gray-900">{row.username}</span>
                        {self ? (
                          <span className="rounded-full bg-accent-light px-2 py-0.5 text-[11px] text-accent">
                            当前
                          </span>
                        ) : null}
                        {rootRow ? (
                          <span className="rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-[11px] text-amber-700">
                            Root
                          </span>
                        ) : null}
                      </div>
                      <div className="mt-0.5 text-xs text-gray-400">ID {row.id}</div>
                    </td>
                    <td className="px-4 py-3">
                      <select
                        value={row.role}
                        disabled={busy || !canManageRole}
                        onChange={(e) => onRoleChange(row, e.target.value as UserRole)}
                        className="h-8 rounded-lg border border-gray-200 bg-white px-2 text-xs text-gray-700 outline-none transition-colors focus:border-accent disabled:opacity-50"
                      >
                        <option value="user">分析用户</option>
                        <option value="admin">管理员</option>
                      </select>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`rounded-full border px-2.5 py-1 text-xs ${
                          active
                            ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                            : 'border-gray-200 bg-gray-50 text-gray-500'
                        }`}
                      >
                        {active ? '启用' : '停用'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-500">{row.created_at || '—'}</td>
                    <td className="px-4 py-3">
                      <div className="flex justify-end gap-2">
                        <button
                          type="button"
                          disabled={!canResetPassword}
                          className="rounded border border-gray-200 bg-white px-2.5 py-1 text-xs text-gray-700 transition-colors hover:bg-gray-50 disabled:opacity-50"
                          onClick={() => onResetPassword(row)}
                        >
                          重置密码
                        </button>
                        <button
                          type="button"
                          disabled={!canToggleActive}
                          className="rounded border border-gray-200 bg-white px-2.5 py-1 text-xs text-gray-700 transition-colors hover:bg-gray-50 disabled:opacity-50"
                          onClick={() => onToggleActive(row)}
                        >
                          {active ? '停用' : '启用'}
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
