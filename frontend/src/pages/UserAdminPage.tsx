import { useCallback, useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import {
  createUserApi,
  deactivateUserApi,
  listUsersApi,
  patchUserApi,
} from '../api/client';
import { useAuth } from '../contexts/useAuth';
import type { AppUserRow } from '../types/auth';
import { logger } from '../lib/logger';

export function UserAdminPage() {
  const { user } = useAuth();
  const [rows, setRows] = useState<AppUserRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({
    username: '',
    password: '',
    role: 'user' as 'admin' | 'user',
  });

  const refresh = useCallback(async () => {
    try {
      const list = await listUsersApi();
      setRows(list);
    } catch (e) {
      logger.error('list users', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void Promise.resolve().then(refresh);
  }, [refresh]);

  if (user?.role !== 'admin') {
    return <Navigate to="/" replace />;
  }

  const onCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.username.trim() || !form.password) return;
    try {
      await createUserApi({
        username: form.username.trim(),
        password: form.password,
        role: form.role,
      });
      setForm({ username: '', password: '', role: 'user' });
      await refresh();
    } catch (err) {
      logger.error('create user', err);
    }
  };

  const toggleActive = async (r: AppUserRow) => {
    const active = typeof r.is_active === 'boolean' ? r.is_active : Boolean(r.is_active);
    try {
      await patchUserApi(r.id, { is_active: !active });
      await refresh();
    } catch (e) {
      logger.error('patch user', e);
    }
  };

  const resetPassword = async (id: number) => {
    const pwd = window.prompt('输入新密码（不少于 1 位）');
    if (!pwd) return;
    try {
      await patchUserApi(id, { password: pwd });
      await refresh();
    } catch (e) {
      logger.error('reset password', e);
    }
  };

  const deactivate = async (id: number) => {
    if (!window.confirm('确定禁用该用户？')) return;
    try {
      await deactivateUserApi(id);
      await refresh();
    } catch (e) {
      logger.error('deactivate user', e);
    }
  };

  return (
    <div className="h-full overflow-y-auto bg-gray-50 p-6">
      <h1 className="mb-4 text-lg font-semibold text-gray-900">用户管理</h1>
      <p className="mb-6 text-sm text-gray-600">
        创建账号并分配角色（admin 可访问全部管理页；user 为普通分析用户）。
      </p>

      <form
        onSubmit={(ev) => void onCreate(ev)}
        className="mb-8 max-w-xl rounded-lg border border-gray-200 bg-white p-4"
      >
        <h2 className="mb-3 text-sm font-medium text-gray-800">新建用户</h2>
        <div className="flex flex-wrap gap-3">
          <input
            placeholder="用户名"
            value={form.username}
            onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))}
            className="rounded border border-gray-300 px-3 py-2 text-sm"
          />
          <input
            type="password"
            placeholder="密码"
            value={form.password}
            onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
            className="rounded border border-gray-300 px-3 py-2 text-sm"
          />
          <select
            value={form.role}
            onChange={(e) =>
              setForm((f) => ({ ...f, role: e.target.value as 'admin' | 'user' }))
            }
            className="rounded border border-gray-300 px-3 py-2 text-sm"
          >
            <option value="user">user</option>
            <option value="admin">admin</option>
          </select>
          <button
            type="submit"
            className="rounded bg-gray-900 px-4 py-2 text-sm text-white hover:bg-gray-800"
          >
            创建
          </button>
        </div>
      </form>

      <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b border-gray-200 bg-gray-50 text-xs text-gray-600">
            <tr>
              <th className="px-4 py-2">ID</th>
              <th className="px-4 py-2">用户名</th>
              <th className="px-4 py-2">角色</th>
              <th className="px-4 py-2">状态</th>
              <th className="px-4 py-2">操作</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-gray-400">
                  加载中…
                </td>
              </tr>
            ) : (
              rows.map((r) => {
                const active =
                  typeof r.is_active === 'boolean' ? r.is_active : Boolean(r.is_active);
                return (
                  <tr key={r.id} className="border-b border-gray-100">
                    <td className="px-4 py-2">{r.id}</td>
                    <td className="px-4 py-2">{r.username}</td>
                    <td className="px-4 py-2">{r.role}</td>
                    <td className="px-4 py-2">{active ? '启用' : '禁用'}</td>
                    <td className="space-x-2 px-4 py-2">
                      <button
                        type="button"
                        className="text-xs text-blue-600 hover:underline"
                        onClick={() => void resetPassword(r.id)}
                      >
                        重置密码
                      </button>
                      <button
                        type="button"
                        className="text-xs text-blue-600 hover:underline"
                        onClick={() => void toggleActive(r)}
                      >
                        {active ? '禁用' : '启用'}
                      </button>
                      <button
                        type="button"
                        className="text-xs text-red-600 hover:underline"
                        onClick={() => void deactivate(r.id)}
                      >
                        禁用（软删）
                      </button>
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
