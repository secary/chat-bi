import { useEffect, useMemo, useState } from 'react';
import type {
  AdminSkillRow,
  MultiAgentsRegistryView,
  MultiAgentsRuntimePayload,
} from '../types/admin';
import {
  getMultiAgentsRegistry,
  listAdminSkills,
  putMultiAgentsRegistry,
} from '../api/client';
import { clampMaxAgentsRound } from '../lib/multiAgentsRegistryUi';
import { logger } from '../lib/logger';

export function MultiAgentsAdminPage() {
  const [skills, setSkills] = useState<AdminSkillRow[]>([]);
  const [draft, setDraft] = useState<MultiAgentsRegistryView | null>(null);
  const [busy, setBusy] = useState(false);
  const [savedHint, setSavedHint] = useState(false);

  const skillSlugsSorted = useMemo(
    () => [...skills].sort((a, b) => a.slug.localeCompare(b.slug)),
    [skills],
  );

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const [reg, sk] = await Promise.all([
          getMultiAgentsRegistry(),
          listAdminSkills(),
        ]);
        if (!cancelled) {
          setDraft({
            ...reg,
            max_manager_rounds:
              typeof reg.max_manager_rounds === 'number' ? reg.max_manager_rounds : 4,
          });
          setSkills(sk);
        }
      } catch (e) {
        logger.error('multi-agents load', e);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const save = async () => {
    if (!draft) return;
    setBusy(true);
    setSavedHint(false);
    try {
      const payload: MultiAgentsRuntimePayload = {
        max_agents_per_round: draft.max_agents_per_round,
        max_manager_rounds: draft.max_manager_rounds,
        agents: Object.fromEntries(
          Object.entries(draft.agents).map(([agentId, meta]) => [agentId, { enabled: meta.enabled }]),
        ),
      };
      const next = await putMultiAgentsRegistry(payload);
      setDraft(next);
      setSavedHint(true);
      window.setTimeout(() => setSavedHint(false), 2500);
    } catch (e) {
      logger.error('multi-agents save', e);
    } finally {
      setBusy(false);
    }
  };

  const updateAgentEnabled = (agentId: string, enabled: boolean) => {
    setDraft((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        agents: {
          ...prev.agents,
          [agentId]: {
            ...prev.agents[agentId],
            enabled,
          },
        },
      };
    });
  };

  const agentIds = draft ? Object.keys(draft.agents).sort((a, b) => a.localeCompare(b)) : [];

  return (
    <div className="flex h-full flex-col gap-4 overflow-auto p-6 lg:p-8">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold tracking-tight text-gray-900">多 Agents 管理</h2>
          <p className="mt-1 text-xs text-gray-500">
            系统内部会自动决定多专线协作。这里仅保留安全运行时开关：执行线启用状态、每轮最多子任务数、协同调度最多轮数。
            技能清单、角色提示和策略边界改为只读观察，避免后台误操作直接影响路由与审计决策。
          </p>
        </div>
        <button
          type="button"
          className="rounded-lg bg-accent px-5 py-2 text-sm text-white transition-colors hover:bg-accent-hover active:scale-[0.98] disabled:opacity-50 disabled:bg-gray-300"
          disabled={busy || !draft}
          onClick={() => void save()}
        >
          保存
        </button>
      </div>

      {savedHint ? (
        <p className="text-sm font-medium text-emerald-600">已保存</p>
      ) : null}

      {!draft ? (
        <p className="text-sm text-gray-400">加载中…</p>
      ) : (
        <>
          <div className="flex flex-wrap items-center gap-4 rounded-xl border border-gray-200 bg-surface p-4 shadow-card">
            <label className="flex items-center gap-2 text-sm text-gray-700">
              每轮最多子任务数
              <input
                type="number"
                min={1}
                max={8}
                className="w-20 rounded-lg border border-gray-200 px-3 py-1.5 text-sm transition-all focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
                value={draft.max_agents_per_round}
                onChange={(e) => {
                  const n = Number(e.target.value);
                  setDraft((p) =>
                    p ? { ...p, max_agents_per_round: clampMaxAgentsRound(n) } : p,
                  );
                }}
              />
              <span className="text-xs text-gray-400">（1–8）</span>
            </label>
            <label className="flex items-center gap-2 text-sm text-gray-700">
              协同调度最多轮数
              <input
                type="number"
                min={1}
                max={8}
                className="w-20 rounded-lg border border-gray-200 px-3 py-1.5 text-sm transition-all focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
                value={draft.max_manager_rounds}
                onChange={(e) => {
                  const n = Number(e.target.value);
                  setDraft((p) =>
                    p ? { ...p, max_manager_rounds: clampMaxAgentsRound(n) } : p,
                  );
                }}
              />
              <span className="text-xs text-gray-400">（1–8，&gt;1 时可多轮调度）</span>
            </label>
          </div>

          <div className="flex flex-col gap-4">
            {agentIds.map((aid) => {
              const meta = draft.agents[aid];
              return (
                <section
                  key={aid}
                  className="rounded-xl border border-gray-200 bg-surface p-5 shadow-card"
                >
                  <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <h3 className="font-mono text-sm font-semibold text-gray-900">{aid}</h3>
                      <p className="mt-1 text-xs text-gray-500">{meta.label || '未配置展示名'}</p>
                    </div>
                    <label className="flex items-center gap-2 text-sm text-gray-700">
                      <span>{meta.enabled ? '已启用' : '已停用'}</span>
                      <input
                        type="checkbox"
                        checked={meta.enabled}
                        onChange={(e) => updateAgentEnabled(aid, e.target.checked)}
                      />
                    </label>
                  </div>
                  <div className="grid gap-3 md:grid-cols-2">
                    <div className="block text-xs text-gray-500">
                      技能模式
                      <div className="mt-1 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-700">
                        {meta.skill_mode === 'restricted' ? 'restricted：仅白名单' : 'dynamic：动态可调'}
                      </div>
                    </div>
                    <div className="block text-xs text-gray-500">
                      执行线状态
                      <div className="mt-1 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-700">
                        {meta.enabled ? '参与系统自动决策' : '已从运行时候选集中移除'}
                      </div>
                    </div>
                  </div>
                  <div className="mt-4 grid gap-4 lg:grid-cols-2">
                    <div>
                      <p className="mb-2 text-xs font-medium tracking-wide text-gray-500">
                        {meta.skill_mode === 'restricted' ? '白名单技能' : '优先技能'}
                      </p>
                      <ul className="grid max-h-48 grid-cols-1 gap-1 overflow-y-auto text-sm sm:grid-cols-2">
                        {meta.skills.map((slug) => {
                          const matched = skillSlugsSorted.find((item) => item.slug === slug);
                          return (
                            <li
                              key={`${aid}-${slug}`}
                              className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-gray-700"
                              title={slug}
                            >
                              {matched?.name || slug}
                              {!matched?.enabled ? (
                                <span className="ml-1 text-xs text-amber-600">（未启用）</span>
                              ) : null}
                            </li>
                          );
                        })}
                        {meta.skills.length === 0 ? (
                          <li className="text-xs text-gray-400">未配置优先技能</li>
                        ) : null}
                      </ul>
                    </div>
                    <div>
                      <p className="mb-2 text-xs font-medium tracking-wide text-gray-500">
                        禁用技能（blocked_skills）
                      </p>
                      <ul className="grid max-h-40 grid-cols-1 gap-1 overflow-y-auto text-sm sm:grid-cols-2">
                        {meta.blocked_skills.map((slug) => {
                          const matched = skillSlugsSorted.find((item) => item.slug === slug);
                          return (
                            <li
                              key={`${aid}-blocked-${slug}`}
                              className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-gray-700"
                              title={slug}
                            >
                              {matched?.name || slug}
                            </li>
                          );
                        })}
                        {meta.blocked_skills.length === 0 ? (
                          <li className="text-xs text-gray-400">未配置禁用技能</li>
                        ) : null}
                      </ul>
                    </div>
                  </div>
                  <div className="mt-4">
                    <p className="mb-2 text-xs font-medium tracking-wide text-gray-500">
                      角色提示（只读）
                    </p>
                    <div className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-3 text-sm leading-6 text-gray-700 whitespace-pre-wrap">
                      {meta.role_prompt || '未配置角色提示'}
                    </div>
                  </div>
                </section>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
