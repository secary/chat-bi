import { useState } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { authEnabled } from '../lib/authFlags';
import { logger } from '../lib/logger';

export function LoginPage() {
  const { user, login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  if (!authEnabled) {
    return <Navigate to="/" replace />;
  }

  if (user) {
    return <Navigate to="/" replace />;
  }

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(username.trim(), password);
    } catch (err) {
      logger.error('login', err);
      setError(err instanceof Error ? err.message : '登录失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-100 px-4">
      <form
        onSubmit={(ev) => void onSubmit(ev)}
        className="w-full max-w-sm rounded-xl border border-gray-200 bg-white p-8 shadow-sm"
      >
        <h1 className="mb-1 text-center text-lg font-semibold text-gray-900">零眸智能 ChatBI</h1>
        <p className="mb-6 text-center text-xs text-gray-500">请登录以访问对话与数据</p>
        <label className="mb-3 block text-xs text-gray-600">
          用户名
          <input
            type="text"
            autoComplete="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
          />
        </label>
        <label className="mb-4 block text-xs text-gray-600">
          密码
          <input
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
          />
        </label>
        {error ? <p className="mb-3 text-xs text-red-600">{error}</p> : null}
        <button
          type="submit"
          disabled={loading || !username.trim() || !password}
          className="w-full rounded-lg bg-gray-900 py-2 text-sm font-medium text-white hover:bg-gray-800 disabled:bg-gray-400"
        >
          {loading ? '登录中…' : '登录'}
        </button>
        <p className="mt-4 text-center text-xs text-gray-400">演示默认账号：admin / admin123</p>
      </form>
    </div>
  );
}
