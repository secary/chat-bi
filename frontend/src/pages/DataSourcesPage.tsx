import { useEffect, useState } from 'react';
import type { CurrentDbConnectionView, DbConnectionRow } from '../types/admin';
import {
  createDbConnectionApi,
  deleteDbConnectionApi,
  getCurrentDbConnection,
  listDbConnections,
  testDbConnectionApi,
  updateDbConnectionApi,
} from '../api/client';
import { logger } from '../lib/logger';

export function DataSourcesPage() {
  const [rows, setRows] = useState<DbConnectionRow[]>([]);
  const [current, setCurrent] = useState<CurrentDbConnectionView | null>(null);
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
      const [list, currentView] = await Promise.all([
        listDbConnections(),
        getCurrentDbConnection(),
      ]);
      setRows(list);
      setCurrent(currentView);
    } catch (e) {
      logger.error('db connections', e);
    }
  };

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const [list, currentView] = await Promise.all([
          listDbConnections(),
          getCurrentDbConnection(),
        ]);
        if (!cancelled) {
          setRows(list);
          setCurrent(currentView);
        }
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
    <div className="h-full overflow-auto p-6 lg:p-8">
      <h2 className="mb-4 text-lg font-semibold tracking-tight text-gray-900">数据源管理</h2>
      {current && (
        <div className="mb-4 rounded-xl border border-accent/20 bg-accent-light p-3.5 text-sm text-accent">
          当前使用中：
          <span className="ml-1 font-medium">
            {current.name}（{current.host}:{current.port}/{current.database_name}）
          </span>
          <span className="ml-2 text-xs text-accent/70">
            来源：{current.source === 'saved_default' ? '管理页默认连接' : '环境变量'}
          </span>
        </div>
      )}

      <div className="mb-6 rounded-xl border border-gray-200 bg-surface p-5 shadow-card">
        <p className="mb-3 text-sm font-medium text-gray-700">
          {editing ? `编辑连接 #${editing}` : '新建连接'}
        </p>
        <div className="grid max-w-xl grid-cols-2 gap-3 text-sm">
          <label className="col-span-2">
            名称
            <input
              className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 transition-all focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            />
          </label>
          <label>
            Host
            <input
              className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 transition-all focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
              value={form.host}
              onChange={(e) => setForm((f) => ({ ...f, host: e.target.value }))}
            />
          </label>
          <label>
            Port
            <input
              type="number"
              className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 transition-all focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
              value={form.port}
              onChange={(e) => setForm((f) => ({ ...f, port: Number(e.target.value) }))}
            />
          </label>
          <label>
            用户
            <input
              className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 transition-all focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
              value={form.username}
              onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))}
            />
          </label>
          <label>
            密码
            <input
              type="password"
              className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 transition-all focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
              value={form.password}
              placeholder={editing ? '不变则留空' : ''}
              onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
            />
          </label>
          <label className="col-span-2">
            数据库名
            <input
              className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 transition-all focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
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
                className="rounded-lg bg-accent px-4 py-2 text-sm text-white transition-colors hover:bg-accent-hover active:scale-[0.98]"
                onClick={() => void submitUpdate()}
              >
                保存修改
              </button>
              <button
                type="button"
                className="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm transition-colors hover:bg-gray-50"
                onClick={() => setEditing(null)}
              >
                取消
              </button>
            </>
          ) : (
            <button
              type="button"
              className="rounded-lg bg-accent px-4 py-2 text-sm text-white transition-colors hover:bg-accent-hover active:scale-[0.98]"
              onClick={() => void submitCreate()}
            >
              添加连接
            </button>
          )}
        </div>
      </div>

      <div className="overflow-x-auto rounded-xl border border-gray-200 bg-surface p-1">
      <table className="w-full border-collapse text-left text-sm">
        <thead>
          <tr className="border-b border-gray-200 text-xs font-medium tracking-wider text-gray-500 uppercase">
            <th className="p-3">名称</th>
            <th className="p-3">Host</th>
            <th className="p-3">库</th>
            <th className="p-3">默认</th>
            <th className="p-3">操作</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id} className="border-b border-gray-100 transition-colors hover:bg-gray-50/50">
              <td className="p-3">{r.name}</td>
              <td className="p-3">
                {r.host}:{r.port}
              </td>
              <td className="p-3">{r.database_name}</td>
              <td className="p-3">
                {r.is_default ? '是' : ''}
                {current?.id === r.id ? '（当前）' : ''}
              </td>
              <td className="space-x-3 p-3">
                <button
                  type="button"
                  className="text-xs text-accent transition-colors hover:text-accent-hover"
                  onClick={() => test(r.id)}
                >
                  测试
                </button>
                <button
                  type="button"
                  className="text-xs text-gray-600 transition-colors hover:text-gray-800"
                  onClick={() => startEdit(r)}
                >
                  编辑
                </button>
                <button
                  type="button"
                  className="text-xs text-red-600 transition-colors hover:text-red-700"
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
    </div>
  );
}
