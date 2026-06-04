import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/useAuth';
import { authEnabled } from '../lib/authFlags';
import { helpTopicForPath } from '../lib/helpDocs';
import { isAdminRole } from '../lib/roles';

const linkCls = ({ isActive }: { isActive: boolean }) =>
  `block rounded-full px-3 py-2 text-sm transition-colors duration-150 ${
    isActive ? 'bg-accent font-medium text-white' : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
  }`;

export function AppLayout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const helpLink = `/help?topic=${helpTopicForPath(location.pathname)}`;

  return (
    <div className="flex h-screen bg-white">
      <aside className="flex h-full min-h-0 w-48 shrink-0 flex-col border-r border-gray-100 bg-white py-5">
        <div className="px-4 pb-5">
          <div className="flex items-center gap-2">
            <img
              src="/logo/lingmou-mark.png"
              alt=""
              aria-hidden="true"
              className="h-7 w-9 shrink-0 object-contain"
            />
            <h1 className="text-base font-semibold text-gray-900">零眸智能</h1>
          </div>
          <p className="text-xs tracking-wide text-gray-500">对话式数据分析</p>
          {user ? (
            <p className="mt-2 truncate text-xs text-gray-500" title={user.username}>
              {user.username}
              <span className="text-gray-400"> · {user.role}</span>
            </p>
          ) : null}
        </div>
        <div className="mx-4 h-px bg-gray-100" />
        <nav className="flex flex-col gap-1 px-3 pt-4">
          <NavLink to="/" end className={linkCls}>
            对话
          </NavLink>
          {isAdminRole(user?.role) ? (
            <>
              <NavLink to="/audits" className={linkCls}>
                审计
              </NavLink>
              <NavLink to="/skills" className={linkCls}>
                技能接入
              </NavLink>
              <NavLink to="/data-sources" className={linkCls}>
                数据源
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
        <div className="mt-auto border-t border-gray-100 px-4 pt-4">
          {authEnabled ? (
            <button
              type="button"
              onClick={() => {
                logout();
                window.location.assign('/login');
              }}
              className="w-full rounded-full border border-gray-200 px-3 py-2 text-xs text-gray-600 transition-colors hover:bg-gray-100"
            >
              退出登录
            </button>
          ) : (
            <p className="text-xs text-amber-700">开发环境：用户登录已关闭</p>
          )}
        </div>
      </aside>
      <main className="relative min-h-0 min-w-0 flex-1 overflow-hidden">
        <NavLink
          to={helpLink}
          className="absolute right-6 top-5 z-20 text-sm font-medium text-accent transition-colors duration-150 hover:text-accent/80"
        >
          文档
        </NavLink>
        <Outlet />
      </main>
    </div>
  );
}
