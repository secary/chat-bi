import { NavLink, Outlet } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { authEnabled } from '../lib/authFlags';

const linkCls = ({ isActive }: { isActive: boolean }) =>
  `block rounded-md px-3 py-2 text-sm ${
    isActive ? 'bg-gray-200 font-medium text-gray-900' : 'text-gray-600 hover:bg-gray-100'
  }`;

export function AppLayout() {
  const { user, logout } = useAuth();

  return (
    <div className="flex h-screen bg-gray-100">
      <aside className="flex h-full min-h-0 w-52 shrink-0 flex-col border-r border-gray-200 bg-white py-4">
        <div className="px-3 pb-3">
          <h1 className="text-sm font-semibold text-gray-900">零眸智能 ChatBI</h1>
          <p className="text-xs text-gray-500">对话式数据分析</p>
          {user ? (
            <p className="mt-2 truncate text-xs text-gray-600" title={user.username}>
              {user.username}
              <span className="text-gray-400"> · {user.role}</span>
            </p>
          ) : null}
        </div>
        <nav className="flex flex-col gap-1 px-2">
          <NavLink to="/" end className={linkCls}>
            对话
          </NavLink>
          <NavLink to="/dashboard" className={linkCls}>
            仪表盘
          </NavLink>
          {user?.role === 'admin' ? (
            <>
              <NavLink to="/multi-agents" className={linkCls}>
                多Agents管理
              </NavLink>
              <NavLink to="/skills" className={linkCls}>
                技能管理
              </NavLink>
              <NavLink to="/data-sources" className={linkCls}>
                数据源管理
              </NavLink>
              <NavLink to="/llm" className={linkCls}>
                LLM配置
              </NavLink>
              <NavLink to="/users" className={linkCls}>
                用户管理
              </NavLink>
            </>
          ) : null}
        </nav>
        <div className="mt-auto border-t border-gray-100 px-3 pt-3">
          {authEnabled ? (
            <button
              type="button"
              onClick={() => {
                logout();
                window.location.assign('/login');
              }}
              className="w-full rounded-md border border-gray-200 px-3 py-2 text-xs text-gray-600 hover:bg-gray-50"
            >
              退出登录
            </button>
          ) : (
            <p className="text-xs text-amber-700">开发环境：用户登录已关闭</p>
          )}
        </div>
      </aside>
      <main className="min-h-0 min-w-0 flex-1 overflow-hidden">
        <Outlet />
      </main>
    </div>
  );
}
