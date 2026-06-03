import { useCallback, useEffect, useMemo, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { createUserApi, listUsersApi, patchUserApi } from '../api/client';
import { useAuth } from '../contexts/useAuth';
import type { AppUserRow } from '../types/auth';
import { logger } from '../lib/logger';
import { UserAdminTable } from '../components/UserAdminTable';

type UserRole = 'admin' | 'user';

function isUserActive(row: AppUserRow): boolean {
  return typeof row.is_active === 'boolean' ? row.is_active : Boolean(row.is_active);
}

export function UserAdminPage() {
  const { user } = useAuth();
  const [rows, setRows] = useState<AppUserRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const [form, setForm] = useState({
    username: '',
    password: '',
    role: 'user' as UserRole,
  });

  const refresh = useCallback(async () => {
    try {
      const list = await listUsersApi();
      setRows(list);
    } catch (e) {
      logger.error('list users', e);
      setError('用户列表读取失败。');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void Promise.resolve().then(refresh);
  }, [refresh]);

  const stats = useMemo(() => {
    const activeCount = rows.filter(isUserActive).length;
    return {
      total: rows.length,
      admins: rows.filter((row) => row.role === 'admin').length,
      active: activeCount,
      inactive: rows.length - activeCount,
    };
  }, [rows]);

  if (user?.role !== 'admin') {
    return <Navigate to="/" replace />;
  }

  const onCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setNotice('');
    if (!form.username.trim() || !form.password) {
      setError('请填写用户名和密码。');
      return;
    }
    try {
      await createUserApi({
        username: form.username.trim(),
        password: form.password,
        role: form.role,
      });
      setForm({ username: '', password: '', role: 'user' });
      setNotice('用户已创建。');
      await refresh();
    } catch (err) {
      logger.error('create user', err);
      setError(err instanceof Error ? err.message : '创建用户失败。');
    }
  };

  const toggleActive = async (row: AppUserRow) => {
    if (row.id === user.id && isUserActive(row)) {
      setError('不能停用当前登录用户。');
      return;
    }
    try {
      setBusyId(row.id);
      setError('');
      await patchUserApi(row.id, { is_active: !isUserActive(row) });
      setNotice(isUserActive(row) ? '用户已停用。' : '用户已启用。');
      await refresh();
    } catch (e) {
      logger.error('patch user', e);
      setError('更新用户状态失败。');
    } finally {
      setBusyId(null);
    }
  };

  const updateRole = async (row: AppUserRow, role: UserRole) => {
    if (role === row.role) return;
    try {
      setBusyId(row.id);
      setError('');
      await patchUserApi(row.id, { role });
      setNotice('用户角色已更新。');
      await refresh();
    } catch (e) {
      logger.error('patch user role', e);
      setError('更新用户角色失败。');
    } finally {
      setBusyId(null);
    }
  };

  const resetPassword = async (row: AppUserRow) => {
    const pwd = window.prompt(`为 ${row.username} 输入新密码`);
    if (!pwd) return;
    try {
      setBusyId(row.id);
      setError('');
      await patchUserApi(row.id, { password: pwd });
      setNotice('密码已重置。');
      await refresh();
    } catch (e) {
      logger.error('reset password', e);
      setError('重置密码失败。');
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="h-full overflow-y-auto bg-gray-50 px-6 py-6 lg:px-8">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-5">
        <header className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-lg font-semibold tracking-tight text-gray-900">用户管理</h1>
            <p className="mt-1 text-sm text-gray-500">创建账号、分配角色并维护登录状态。</p>
          </div>
        </header>

        <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {[
            ['全部账号', stats.total],
            ['管理员', stats.admins],
            ['启用', stats.active],
            ['停用', stats.inactive],
          ].map(([label, value]) => (
            <div key={label} className="rounded-lg border border-gray-200 bg-white px-4 py-3 shadow-card">
              <div className="text-xs text-gray-500">{label}</div>
              <div className="mt-1 text-2xl font-semibold text-gray-900">{value}</div>
            </div>
          ))}
        </section>

        <section className="grid gap-5 lg:grid-cols-[360px_minmax(0,1fr)]">
          <form
            onSubmit={(ev) => void onCreate(ev)}
            className="rounded-lg border border-gray-200 bg-white p-5 shadow-card"
          >
            <div className="mb-4">
              <h2 className="text-sm font-semibold text-gray-900">新建用户</h2>
            </div>
            <div className="space-y-3">
              <label className="block text-xs font-medium text-gray-500">
                用户名
                <input
                  value={form.username}
                  onChange={(e) => setForm((prev) => ({ ...prev, username: e.target.value }))}
                  className="mt-1.5 h-10 w-full rounded-lg border border-gray-200 px-3 text-sm transition-all focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30"
                  placeholder="例如 analyst"
                />
              </label>
              <label className="block text-xs font-medium text-gray-500">
                初始密码
                <input
                  type="password"
                  value={form.password}
                  onChange={(e) => setForm((prev) => ({ ...prev, password: e.target.value }))}
                  className="mt-1.5 h-10 w-full rounded-lg border border-gray-200 px-3 text-sm transition-all focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30"
                  placeholder="输入初始密码"
                />
              </label>
              <label className="block text-xs font-medium text-gray-500">
                角色
                <select
                  value={form.role}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, role: e.target.value as UserRole }))
                  }
                  className="mt-1.5 h-10 w-full rounded-lg border border-gray-200 bg-white px-3 text-sm transition-all focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30"
                >
                  <option value="user">分析用户</option>
                  <option value="admin">管理员</option>
                </select>
              </label>
              <button
                type="submit"
                className="h-10 w-full rounded-lg bg-accent px-4 text-sm font-medium text-white transition-colors hover:bg-accent-hover active:scale-[0.98]"
              >
                创建用户
              </button>
            </div>
            {notice || error ? (
              <div
                className={`mt-4 rounded-lg border px-3 py-2 text-sm ${
                  error
                    ? 'border-red-200 bg-red-50 text-red-700'
                    : 'border-emerald-200 bg-emerald-50 text-emerald-700'
                }`}
              >
                {error || notice}
              </div>
            ) : null}
          </form>

          <UserAdminTable
            rows={rows}
            loading={loading}
            busyId={busyId}
            currentUserId={user.id}
            onRoleChange={(row, role) => void updateRole(row, role)}
            onResetPassword={(row) => void resetPassword(row)}
            onToggleActive={(row) => void toggleActive(row)}
            isActive={isUserActive}
          />
        </section>
      </div>
    </div>
  );
}
