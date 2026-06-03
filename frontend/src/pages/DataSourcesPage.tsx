import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  createDbConnection,
  deleteDbConnection,
  getCurrentDbConnection,
  listDbConnections,
  testDbConnection,
  updateDbConnection,
} from '../api/client';
import type {
  DbConnectionCurrent,
  DbConnectionPayload,
  DbConnectionRow,
} from '../types/admin';
import { logger } from '../lib/logger';

const EMPTY_FORM = {
  name: '',
  host: '',
  port: '3306',
  username: '',
  password: '',
  database_name: '',
  is_default: false,
};

type FormState = typeof EMPTY_FORM;

function payloadFromForm(form: FormState): DbConnectionPayload {
  return {
    name: form.name.trim(),
    host: form.host.trim(),
    port: Number(form.port) || 3306,
    username: form.username.trim(),
    password: form.password,
    database_name: form.database_name.trim(),
    is_default: form.is_default,
  };
}

function formFromRow(row: DbConnectionRow): FormState {
  return {
    name: row.name,
    host: row.host,
    port: String(row.port || 3306),
    username: row.username,
    password: '',
    database_name: row.database_name,
    is_default: Boolean(row.is_default),
  };
}

function connectionLabel(row: Pick<DbConnectionRow, 'host' | 'port' | 'database_name'>): string {
  return `${row.host}:${row.port}/${row.database_name}`;
}

function currentConnectionName(current: DbConnectionCurrent): string {
  if (current.source === 'env') return '默认连接';
  return current.name;
}

export function DataSourcesPage() {
  const [rows, setRows] = useState<DbConnectionRow[]>([]);
  const [current, setCurrent] = useState<DbConnectionCurrent | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [busy, setBusy] = useState(false);
  const [testingId, setTestingId] = useState<number | null>(null);
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');

  const selected = useMemo(
    () => rows.find((item) => item.id === selectedId) || null,
    [rows, selectedId],
  );

  const refresh = useCallback(async () => {
    const [nextRows, nextCurrent] = await Promise.all([
      listDbConnections(),
      getCurrentDbConnection(),
    ]);
    setRows(nextRows);
    setCurrent(nextCurrent);
    if (selectedId != null && !nextRows.some((item) => item.id === selectedId)) {
      setSelectedId(null);
      setForm(EMPTY_FORM);
    }
  }, [selectedId]);

  useEffect(() => {
    let cancelled = false;
    void Promise.all([listDbConnections(), getCurrentDbConnection()])
      .then(([nextRows, nextCurrent]) => {
        if (cancelled) return;
        setRows(nextRows);
        setCurrent(nextCurrent);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        logger.error('load db connections', err);
        setError(String(err));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const selectRow = (row: DbConnectionRow) => {
    setSelectedId(row.id);
    setForm(formFromRow(row));
    setNotice('');
    setError('');
  };

  const newConnection = () => {
    setSelectedId(null);
    setForm(EMPTY_FORM);
    setNotice('');
    setError('');
  };

  const submit = async () => {
    setBusy(true);
    setNotice('');
    setError('');
    try {
      const payload = payloadFromForm(form);
      if (!payload.name || !payload.host || !payload.username || !payload.database_name) {
        setError('请填写名称、主机、用户名和数据库名。');
        return;
      }
      if (selectedId == null) {
        const created = await createDbConnection(payload);
        setSelectedId(created.id);
        setForm(formFromRow(created));
        setNotice('数据源已创建。');
      } else {
        const updatePayload = { ...payload };
        if (!form.password) {
          delete updatePayload.password;
        }
        const updated = await updateDbConnection(selectedId, updatePayload);
        setForm(formFromRow(updated));
        setNotice('数据源已保存。');
      }
      await refresh();
    } catch (err) {
      logger.error('save db connection', err);
      setError(String(err));
    } finally {
      setBusy(false);
    }
  };

  const runTest = async (id: number) => {
    setTestingId(id);
    setNotice('');
    setError('');
    try {
      await testDbConnection(id);
      setNotice('连接测试通过。');
    } catch (err) {
      logger.error('test db connection', err);
      setError(String(err));
    } finally {
      setTestingId(null);
    }
  };

  const remove = async (id: number) => {
    if (!window.confirm('删除这个数据源连接？')) return;
    setBusy(true);
    setNotice('');
    setError('');
    try {
      await deleteDbConnection(id);
      if (selectedId === id) newConnection();
      await refresh();
      setNotice('数据源已删除。');
    } catch (err) {
      logger.error('delete db connection', err);
      setError(String(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex h-full min-h-0 flex-col bg-white">
      <header className="border-b border-gray-100 px-6 py-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">数据源接入</h2>
            <p className="mt-1 text-sm text-gray-500">维护外部 MySQL 连接，并选择问数默认来源。</p>
          </div>
        </div>
      </header>

      <div className="grid min-h-0 flex-1 grid-cols-[minmax(280px,360px)_1fr] overflow-hidden">
        <section className="min-h-0 overflow-y-auto border-r border-gray-100 p-4">
          <div className="mb-4 rounded-lg border border-gray-200 bg-gray-50 px-3 py-3">
            <p className="text-xs font-medium text-gray-500">当前生效</p>
            {current ? (
              <>
                <p className="mt-1 truncate text-sm font-medium text-gray-900">
                  {currentConnectionName(current)}
                </p>
                <p className="mt-1 truncate font-mono text-xs text-gray-500">
                  {connectionLabel(current)}
                </p>
              </>
            ) : (
              <p className="mt-1 text-sm text-gray-500">加载中…</p>
            )}
          </div>
          <div className="space-y-2">
            {rows.map((row) => (
              <button
                key={row.id}
                type="button"
                onClick={() => selectRow(row)}
                className={`w-full rounded-lg border px-3 py-3 text-left transition-colors ${
                  selectedId === row.id
                    ? 'border-accent bg-accent-light'
                    : 'border-gray-200 hover:border-accent hover:bg-accent-light'
                }`}
              >
                <div className="flex items-center gap-2">
                  <span className="truncate text-sm font-medium text-gray-900">{row.name}</span>
                  {row.is_default ? (
                    <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] text-emerald-700">
                      默认
                    </span>
                  ) : null}
                </div>
                <p className="mt-1 truncate font-mono text-xs text-gray-500">
                  {connectionLabel(row)}
                </p>
                <p className="mt-1 truncate text-xs text-gray-400">用户：{row.username}</p>
              </button>
            ))}
            <button
              type="button"
              onClick={newConnection}
              className="flex min-h-20 w-full items-center justify-center rounded-lg border border-dashed border-accent/60 px-3 py-6 text-sm font-medium text-gray-700 transition-colors hover:border-accent hover:bg-accent-light focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2"
            >
              + 新建数据源
            </button>
          </div>
        </section>

        <section className="min-h-0 overflow-y-auto px-6 py-5">
          <div className="max-w-3xl">
            <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="text-base font-semibold text-gray-900">
                  {selected ? '编辑连接' : '新建连接'}
                </h3>
                <p className="mt-1 text-sm text-gray-500">
                  目前支持 MySQL；保存为默认后，未指定数据源的对话会使用该连接。
                </p>
              </div>
              {selected ? (
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => void runTest(selected.id)}
                    disabled={testingId === selected.id}
                    className="rounded-full border border-gray-200 px-3 py-1.5 text-xs text-gray-700 transition-colors hover:bg-gray-50 disabled:opacity-50"
                  >
                    {testingId === selected.id ? '测试中…' : '测试连接'}
                  </button>
                  <button
                    type="button"
                    onClick={() => void remove(selected.id)}
                    disabled={busy}
                    className="rounded-full border border-red-100 px-3 py-1.5 text-xs text-red-600 transition-colors hover:bg-red-50 disabled:opacity-50"
                  >
                    删除
                  </button>
                </div>
              ) : null}
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <label className="block">
                <span className="text-xs font-medium text-gray-600">名称</span>
                <input
                  value={form.name}
                  onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
                  className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-accent"
                  placeholder="零眸测试库"
                />
              </label>
              <label className="block">
                <span className="text-xs font-medium text-gray-600">数据库名</span>
                <input
                  value={form.database_name}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, database_name: e.target.value }))
                  }
                  className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-accent"
                  placeholder="chatbi_demo"
                />
              </label>
              <label className="block">
                <span className="text-xs font-medium text-gray-600">主机</span>
                <input
                  value={form.host}
                  onChange={(e) => setForm((prev) => ({ ...prev, host: e.target.value }))}
                  className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-accent"
                  placeholder="127.0.0.1"
                />
              </label>
              <label className="block">
                <span className="text-xs font-medium text-gray-600">端口</span>
                <input
                  value={form.port}
                  onChange={(e) => setForm((prev) => ({ ...prev, port: e.target.value }))}
                  inputMode="numeric"
                  className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-accent"
                  placeholder="3306"
                />
              </label>
              <label className="block">
                <span className="text-xs font-medium text-gray-600">用户名</span>
                <input
                  value={form.username}
                  onChange={(e) => setForm((prev) => ({ ...prev, username: e.target.value }))}
                  className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-accent"
                  placeholder="demo_user"
                />
              </label>
              <label className="block">
                <span className="text-xs font-medium text-gray-600">
                  密码{selected ? '（留空则不修改）' : ''}
                </span>
                <input
                  type="password"
                  value={form.password}
                  onChange={(e) => setForm((prev) => ({ ...prev, password: e.target.value }))}
                  className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-accent"
                  placeholder={selected ? '保持原密码' : '连接密码'}
                />
              </label>
            </div>

            <label className="mt-5 flex items-center gap-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={form.is_default}
                onChange={(e) => setForm((prev) => ({ ...prev, is_default: e.target.checked }))}
                className="h-4 w-4 rounded border-gray-300 text-accent"
              />
              设为默认数据源
            </label>

            <div className="mt-6 flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={() => void submit()}
                disabled={busy}
                className="rounded-full bg-accent px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-hover disabled:opacity-50"
              >
                {busy ? '保存中…' : '保存数据源'}
              </button>
              {notice ? <span className="text-sm text-emerald-700">{notice}</span> : null}
              {error ? <span className="text-sm text-red-600">{error}</span> : null}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
