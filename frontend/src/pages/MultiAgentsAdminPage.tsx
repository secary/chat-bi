import { useEffect, useMemo, useState } from 'react';
import type { AdminSkillRow, MultiAgentsRegistryPayload } from '../types/admin';
import {
  getMultiAgentsRegistry,
  listAdminSkills,
  putMultiAgentsRegistry,
} from '../api/client';
import { clampMaxAgentsRound, isValidAgentId } from '../lib/multiAgentsRegistryUi';
import { logger } from '../lib/logger';

function emptyEntry() {
  return { label: '', role_prompt: '', skills: [] as string[] };
}

export function MultiAgentsAdminPage() {
  const [skills, setSkills] = useState<AdminSkillRow[]>([]);
  const [draft, setDraft] = useState<MultiAgentsRegistryPayload | null>(null);
  const [newId, setNewId] = useState('');
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
          setDraft(reg);
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
      const next = await putMultiAgentsRegistry(draft);
      setDraft(next);
      setSavedHint(true);
      window.setTimeout(() => setSavedHint(false), 2500);
    } catch (e) {
      logger.error('multi-agents save', e);
    } finally {
      setBusy(false);
    }
  };

  const updateAgent = (
    agentId: string,
    patch: Partial<{ label: string; role_prompt: string; skills: string[] }>,
  ) => {
    setDraft((prev) => {
      if (!prev) return prev;
      const cur = prev.agents[agentId] ?? emptyEntry();
      return {
        ...prev,
        agents: {
          ...prev.agents,
          [agentId]: {
            label: patch.label ?? cur.label,
            role_prompt: patch.role_prompt ?? cur.role_prompt,
            skills: patch.skills ?? cur.skills,
          },
        },
      };
    });
  };

  const toggleSkill = (agentId: string, slug: string, checked: boolean) => {
    setDraft((prev) => {
      if (!prev) return prev;
      const cur = prev.agents[agentId] ?? emptyEntry();
      const set = new Set(cur.skills);
      if (checked) set.add(slug);
      else set.delete(slug);
      return {
        ...prev,
        agents: {
          ...prev.agents,
          [agentId]: { ...cur, skills: [...set].sort((a, b) => a.localeCompare(b)) },
        },
      };
    });
  };

  const addAgent = () => {
    const id = newId.trim();
    if (!id || !isValidAgentId(id)) return;
    setDraft((prev) => {
      if (!prev || prev.agents[id]) return prev;
      return {
        ...prev,
        agents: { ...prev.agents, [id]: emptyEntry() },
      };
    });
    setNewId('');
  };

  const removeAgent = (agentId: string) => {
    if (!window.confirm(`删除专线「${agentId}」？`)) return;
    setDraft((prev) => {
      if (!prev) return prev;
      const nextAgents = { ...prev.agents };
      delete nextAgents[agentId];
      return { ...prev, agents: nextAgents };
    });
  };

  const agentIds = draft ? Object.keys(draft.agents).sort((a, b) => a.localeCompare(b)) : [];

  return (
    <div className="flex h-full flex-col gap-4 overflow-auto p-6 lg:p-8">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold tracking-tight text-gray-900">多 Agents 管理</h2>
          <p className="mt-1 text-xs text-gray-500">
            配置每条专线的展示名、角色提示与可用技能。全局禁用的技能仍可勾选；运行时仅与已启用技能求交集。
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
          <div className="flex flex-wrap items-center gap-3 rounded-xl border border-gray-200 bg-surface p-4 shadow-card">
            <label className="flex items-center gap-2 text-sm text-gray-700">
              每轮最多专线数
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
          </div>

          <div className="flex flex-wrap gap-2 rounded-xl border border-gray-200 bg-surface p-4 shadow-card">
            <input
              className="max-w-xs flex-1 rounded-lg border border-gray-200 px-3 py-1.5 text-sm transition-all focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
              placeholder="新专线 id（字母数字开头）"
              value={newId}
              onChange={(e) => setNewId(e.target.value)}
            />
            <button
              type="button"
              className="rounded-lg border border-gray-200 bg-white px-4 py-1.5 text-sm text-gray-700 transition-colors hover:bg-gray-50 disabled:opacity-50"
              disabled={busy || !newId.trim()}
              onClick={() => addAgent()}
            >
              添加专线
            </button>
          </div>

          <div className="flex flex-col gap-4">
            {agentIds.map((aid) => {
              const meta = draft.agents[aid] ?? emptyEntry();
              return (
                <section
                  key={aid}
                  className="rounded-xl border border-gray-200 bg-surface p-5 shadow-card"
                >
                  <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                    <h3 className="font-mono text-sm font-semibold text-gray-900">{aid}</h3>
                    <button
                      type="button"
                      className="text-xs text-red-600 transition-colors hover:text-red-700"
                      onClick={() => removeAgent(aid)}
                    >
                      删除专线
                    </button>
                  </div>
                  <div className="grid gap-3 md:grid-cols-2">
                    <label className="block text-xs text-gray-500">
                      展示名
                      <input
                        className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-1.5 text-sm transition-all focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
                        value={meta.label}
                        onChange={(e) => updateAgent(aid, { label: e.target.value })}
                      />
                    </label>
                    <div className="md:col-span-2">
                      <label className="block text-xs text-gray-500">
                        角色提示（role_prompt）
                        <textarea
                          className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm transition-all focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
                          rows={3}
                          value={meta.role_prompt}
                          onChange={(e) => updateAgent(aid, { role_prompt: e.target.value })}
                        />
                      </label>
                    </div>
                  </div>
                  <p className="mb-2 mt-3 text-xs font-medium tracking-wide text-gray-500">可用技能</p>
                  <ul className="grid max-h-48 grid-cols-1 gap-1 overflow-y-auto text-sm sm:grid-cols-2 lg:grid-cols-3">
                    {skillSlugsSorted.map((s) => (
                      <li key={`${aid}-${s.slug}`}>
                        <label className="flex cursor-pointer items-center gap-2 rounded-lg px-2 py-1 transition-colors hover:bg-gray-50">
                          <input
                            type="checkbox"
                            checked={meta.skills.includes(s.slug)}
                            onChange={(e) => toggleSkill(aid, s.slug, e.target.checked)}
                          />
                          <span className="truncate" title={s.slug}>
                            {s.name || s.slug}
                            {!s.enabled ? (
                              <span className="ml-1 text-xs text-amber-600">（未启用）</span>
                            ) : null}
                          </span>
                        </label>
                      </li>
                    ))}
                  </ul>
                </section>
              );
            })}
          </div>

          {agentIds.length === 0 ? (
            <p className="text-sm text-amber-700">请至少添加一条专线后再保存。</p>
          ) : null}
        </>
      )}
    </div>
  );
}
