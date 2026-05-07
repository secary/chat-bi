import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

export function RequireAuth() {
  const { user, ready } = useAuth();

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
