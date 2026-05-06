import { useEffect, useState } from 'react';
import type { DbConnectionRow } from '../types/admin';
import {
  createDbConnectionApi,
  deleteDbConnectionApi,
  listDbConnections,
  testDbConnectionApi,
  updateDbConnectionApi,
} from '../api/client';
import { logger } from '../lib/logger';

export function DataSourcesPage() {
  const [rows, setRows] = useState<DbConnectionRow[]>([]);
  const [editing, setEditing] = useState<number | null>(null);
  const [form, setForm] = useState({
    name: '',
    host: '127.0.0.1',
    port: 3307,
    username: '',
    password: '',
    database_name: 'chatbi_demo',
    is_default: false,
  });

  const refresh = async () => {
    try {
      setRows(await listDbConnections());
    } catch (e) {
      logger.error('db connections', e);
    }
  };

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const list = await listDbConnections();
        if (!cancelled) setRows(list);
      } catch (e) {
        logger.error('db connections', e);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const startEdit = (r: DbConnectionRow) => {
    setEditing(r.id);
    setForm({
      name: r.name,
      host: r.host,
      port: r.port,
      username: r.username,
      password: '',
      database_name: r.database_name,
      is_default: !!r.is_default,
    });
  };

  const submitCreate = async () => {
    try {
      await createDbConnectionApi({
        name: form.name,
        host: form.host,
        port: form.port,
        username: form.username,
        password: form.password,
        database_name: form.database_name,
        is_default: form.is_default,
      });
      await refresh();
      setForm({
        name: '',
        host: '127.0.0.1',
        port: 3307,
        username: '',
        password: '',
        database_name: 'chatbi_demo',
        is_default: false,
      });
    } catch (e) {
      logger.error('create connection', e);
    }
  };

  const submitUpdate = async () => {
    if (editing == null) return;
    try {
      await updateDbConnectionApi(editing, {
        name: form.name,
        host: form.host,
        port: form.port,
        username: form.username,
        password: form.password || undefined,
        database_name: form.database_name,
        is_default: form.is_default,
      });
      setEditing(null);
      await refresh();
    } catch (e) {
      logger.error('update connection', e);
    }
  };

  const test = async (id: number) => {
    try {
      await testDbConnectionApi(id);
      window.alert('连接成功');
    } catch (e) {
      logger.error('test connection', e);
      window.alert(e instanceof Error ? e.message : String(e));
    }
  };

  const remove = async (id: number) => {
    if (!window.confirm('删除该数据源连接？')) return;
    try {
      await deleteDbConnectionApi(id);
      await refresh();
    } catch (e) {
      logger.error('delete connection', e);
    }
  };

  return (
    <div className="h-full overflow-auto p-6">
      <h2 className="mb-4 text-lg font-semibold text-gray-900">数据源管理</h2>

      <div className="mb-6 rounded-lg border border-gray-200 bg-white p-4">
        <p className="mb-3 text-sm font-medium text-gray-700">
          {editing ? `编辑连接 #${editing}` : '新建连接'}
        </p>
        <div className="grid max-w-xl grid-cols-2 gap-3 text-sm">
          <label className="col-span-2">
            名称
            <input
              className="mt-1 w-full rounded border border-gray-300 px-2 py-1"
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            />
          </label>
          <label>
            Host
            <input
              className="mt-1 w-full rounded border border-gray-300 px-2 py-1"
              value={form.host}
              onChange={(e) => setForm((f) => ({ ...f, host: e.target.value }))}
            />
          </label>
          <label>
            Port
            <input
              type="number"
              className="mt-1 w-full rounded border border-gray-300 px-2 py-1"
              value={form.port}
              onChange={(e) => setForm((f) => ({ ...f, port: Number(e.target.value) }))}
            />
          </label>
          <label>
            用户
            <input
              className="mt-1 w-full rounded border border-gray-300 px-2 py-1"
              value={form.username}
              onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))}
            />
          </label>
          <label>
            密码
            <input
              type="password"
              className="mt-1 w-full rounded border border-gray-300 px-2 py-1"
              value={form.password}
              placeholder={editing ? '不变则留空' : ''}
              onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
            />
          </label>
          <label className="col-span-2">
            数据库名
            <input
              className="mt-1 w-full rounded border border-gray-300 px-2 py-1"
              value={form.database_name}
              onChange={(e) => setForm((f) => ({ ...f, database_name: e.target.value }))}
            />
          </label>
          <label className="col-span-2 flex items-center gap-2">
            <input
              type="checkbox"
              checked={form.is_default}
              onChange={(e) => setForm((f) => ({ ...f, is_default: e.target.checked }))}
            />
            设为默认（Skill 脚本使用）
          </label>
        </div>
        <div className="mt-3 flex gap-2">
          {editing ? (
            <>
              <button
                type="button"
                className="rounded bg-blue-600 px-3 py-1 text-sm text-white"
                onClick={() => void submitUpdate()}
              >
                保存修改
              </button>
              <button
                type="button"
                className="rounded border border-gray-300 px-3 py-1 text-sm"
                onClick={() => setEditing(null)}
              >
                取消
              </button>
            </>
          ) : (
            <button
              type="button"
              className="rounded bg-gray-900 px-3 py-1 text-sm text-white"
              onClick={() => void submitCreate()}
            >
              添加连接
            </button>
          )}
        </div>
      </div>

      <table className="w-full border-collapse text-left text-sm">
        <thead>
          <tr className="border-b border-gray-200 bg-gray-50">
            <th className="p-2">名称</th>
            <th className="p-2">Host</th>
            <th className="p-2">库</th>
            <th className="p-2">默认</th>
            <th className="p-2">操作</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id} className="border-b border-gray-100">
              <td className="p-2">{r.name}</td>
              <td className="p-2">
                {r.host}:{r.port}
              </td>
              <td className="p-2">{r.database_name}</td>
              <td className="p-2">{r.is_default ? '是' : ''}</td>
              <td className="space-x-2 p-2">
                <button
                  type="button"
                  className="text-blue-600 hover:underline"
                  onClick={() => test(r.id)}
                >
                  测试
                </button>
                <button
                  type="button"
                  className="text-gray-700 hover:underline"
                  onClick={() => startEdit(r)}
                >
                  编辑
                </button>
                <button
                  type="button"
                  className="text-red-600 hover:underline"
                  onClick={() => void remove(r.id)}
                >
                  删除
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
