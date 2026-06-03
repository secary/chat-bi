import { useMemo, useState } from 'react';
import { useAuth } from '../contexts/useAuth';
import { helpDocTabs, type DocSection, type DocTab } from '../lib/helpDocs';

function SectionBlock({ section }: { section: DocSection }) {
  return (
    <section className="border-t border-gray-200 py-6 first:border-t-0 first:pt-0">
      <h2 className="text-lg font-semibold text-gray-900">{section.title}</h2>
      {section.body ? <p className="mt-3 text-sm leading-6 text-gray-700">{section.body}</p> : null}
      {section.items ? (
        <ul className="mt-3 space-y-2 text-sm leading-6 text-gray-700">
          {section.items.map((item) => (
            <li key={item} className="flex gap-2">
              <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      ) : null}
      {section.table ? (
        <div className="mt-4 overflow-hidden rounded-lg border border-gray-200">
          <table className="w-full border-collapse text-left text-sm">
            <thead className="bg-gray-50 text-gray-600">
              <tr>
                {section.table.headers.map((header) => (
                  <th key={header} className="px-4 py-3 font-medium">
                    {header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 text-gray-700">
              {section.table.rows.map((row) => (
                <tr key={row.join('|')}>
                  {row.map((cell) => (
                    <td key={cell} className="px-4 py-3 align-top">
                      {cell}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}

export function HelpPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';
  const visibleTabs = useMemo(() => helpDocTabs.filter((tab) => tab.id === 'user' || isAdmin), [isAdmin]);
  const [activeId, setActiveId] = useState<DocTab['id']>('user');
  const activeTab = visibleTabs.find((tab) => tab.id === activeId) ?? visibleTabs[0];

  return (
    <div className="h-full overflow-y-auto bg-white">
      <div className="mx-auto max-w-5xl px-8 py-8">
        <header className="mb-7">
          <p className="text-sm font-medium text-accent">帮助文档</p>
          <h1 className="mt-2 text-2xl font-semibold text-gray-950">ChatBI 使用与维护说明</h1>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-gray-600">
            文档会按当前登录角色展示。普通用户只看到业务使用说明，管理员可查看配置、运维和开发相关内容。
          </p>
        </header>

        <div className="mb-7 flex flex-wrap gap-2 border-b border-gray-200 pb-3">
          {visibleTabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveId(tab.id)}
              className={`rounded-full px-4 py-2 text-sm transition-colors ${
                activeTab.id === tab.id
                  ? 'bg-accent text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200 hover:text-gray-900'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="mb-6">
          <h2 className="text-xl font-semibold text-gray-900">{activeTab.label}</h2>
          <p className="mt-2 text-sm leading-6 text-gray-600">{activeTab.intro}</p>
        </div>

        <div className="pb-10">
          {activeTab.sections.map((section) => (
            <SectionBlock key={section.title} section={section} />
          ))}
        </div>
      </div>
    </div>
  );
}
