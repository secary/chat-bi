import { NavLink, Outlet } from 'react-router-dom';

const linkCls = ({ isActive }: { isActive: boolean }) =>
  `block rounded-md px-3 py-2 text-sm ${
    isActive ? 'bg-gray-200 font-medium text-gray-900' : 'text-gray-600 hover:bg-gray-100'
  }`;

export function AppLayout() {
  return (
    <div className="flex h-screen bg-gray-100">
      <aside className="flex w-52 shrink-0 flex-col border-r border-gray-200 bg-white py-4">
        <div className="px-3 pb-3">
          <h1 className="text-sm font-semibold text-gray-900">零眸智能 ChatBI</h1>
          <p className="text-xs text-gray-500">对话式数据分析</p>
        </div>
        <nav className="flex flex-col gap-1 px-2">
          <NavLink to="/" end className={linkCls}>
            对话
          </NavLink>
          <NavLink to="/dashboard" className={linkCls}>
            仪表盘
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
        </nav>
      </aside>
      <main className="min-h-0 min-w-0 flex-1 overflow-hidden">
        <Outlet />
      </main>
    </div>
  );
}
