import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../contexts/useAuth';
import { authEnabled } from '../lib/authFlags';

export function RequireAuth() {
  const { user, ready } = useAuth();

  if (!authEnabled) {
    return <Outlet />;
  }

  if (!ready) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-100 text-sm text-gray-500">
        加载中…
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
