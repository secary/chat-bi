import { useEffect, useState } from 'react';
import type { AdminSkillRow, SkillAuditRow } from '../types/admin';
import {
  createSkillApi,
  getSkillFile,
  listAdminSkills,
  listSkillAudits,
} from '../api/client';
import { logger } from '../lib/logger';

export function SkillAdminPage() {
  const [skills, setSkills] = useState<AdminSkillRow[]>([]);
  const [audits, setAudits] = useState<SkillAuditRow[]>([]);
  const [slug, setSlug] = useState<string | null>(null);
  const [markdown, setMarkdown] = useState('');
  const [newSlug, setNewSlug] = useState('');
  const [busy, setBusy] = useState(false);

  const refresh = async () => {
    try {
      setSkills(await listAdminSkills());
      setAudits((await listSkillAudits()).items);
    } catch (e) {
      logger.error('skills list', e);
    }
  };

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const [skillsData, auditData] = await Promise.all([listAdminSkills(), listSkillAudits()]);
        if (!cancelled) {
          setSkills(skillsData);
          setAudits(auditData.items);
        }
      } catch (e) {
        logger.error('skills list', e);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const selectSkill = async (s: string) => {
    setBusy(true);
    setSlug(s);
    try {
      const f = await getSkillFile(s);
      setMarkdown(f.markdown);
    } catch (e) {
      logger.error('load skill file', e);
    } finally {
      setBusy(false);
    }
  };

  const create = async () => {
    const sl = newSlug.trim();
    if (!sl) return;
    setBusy(true);
    try {
      await createSkillApi(sl);
      setNewSlug('');
      await refresh();
      await selectSkill(sl);
    } catch (e) {
      logger.error('create skill', e);
    } finally {
      setBusy(false);
    }
  };

  const selectedAudit = audits.find((item) => item.slug === slug) || null;
  const readyCount = audits.filter((item) => item.status === 'ok').length;
  const warningCount = audits.filter((item) => item.status === 'warning').length;
  const errorCount = audits.filter((item) => item.status === 'error').length;
  const topIssues = selectedAudit?.issues.slice(0, 3) ?? [];

  return (
    <div className="flex h-full min-h-0 flex-col bg-white">
      <header className="bg-white px-6 py-7">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-5">
          <div>
            <h2 className="text-[26px] font-semibold leading-tight tracking-normal text-gray-950">技能接入</h2>
            <p className="mt-1 text-xs text-gray-500">
              只保留新能力接入与审核，不承载日常技能运维。
            </p>
          </div>
          <div className="flex flex-wrap gap-3 rounded-[28px] border border-gray-200 bg-white p-3 shadow-[0_18px_55px_rgba(15,23,42,0.08)]">
            <input
              className="min-w-[220px] flex-1 rounded-full border border-transparent bg-gray-50 px-4 py-2.5 text-sm transition-all placeholder:text-gray-400 focus:border-accent focus:bg-white focus:outline-none focus:ring-2 focus:ring-accent/30"
              placeholder="新技能 slug"
              value={newSlug}
              onChange={(e) => setNewSlug(e.target.value)}
            />
            <button
              type="button"
              className="whitespace-nowrap rounded-full bg-gray-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-gray-800 disabled:opacity-50"
              disabled={busy || !newSlug.trim()}
              onClick={() => void create()}
            >
              创建接入项
            </button>
          </div>
          <div className="flex flex-wrap gap-2 text-xs text-gray-600">
            <span className="rounded-full border border-gray-200 px-3 py-1">可直接纳入 {readyCount}</span>
            <span className="rounded-full border border-gray-200 px-3 py-1">待补信息 {warningCount}</span>
            <span className="rounded-full border border-gray-200 px-3 py-1">阻塞缺口 {errorCount}</span>
          </div>
        </div>
      </header>

      <div className="min-h-0 flex-1 overflow-auto px-6 pb-8 lg:px-8">
        <div className="mx-auto grid w-full max-w-6xl gap-5 xl:grid-cols-[320px_minmax(0,1fr)]">
          <section className="min-h-0 rounded-2xl border border-gray-200 bg-white p-4 shadow-[0_16px_42px_rgba(15,23,42,0.06)]">
            <div className="mb-3 flex items-center justify-between gap-2">
              <p className="text-sm font-semibold text-gray-900">已接入技能</p>
              <span className="text-xs text-gray-400">{skills.length}</span>
            </div>
            <ul className="max-h-[calc(100vh-240px)] space-y-1 overflow-y-auto pr-1 text-sm">
              {skills.map((s) => (
                <li key={s.slug}>
                  <button
                    type="button"
                    className={`w-full rounded-xl border px-3 py-2.5 text-left transition-colors hover:border-gray-200 hover:bg-gray-50 ${
                      slug === s.slug ? 'border-accent bg-accent-light font-medium text-accent' : 'border-transparent'
                    }`}
                    onClick={() => void selectSkill(s.slug)}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate">{s.name || s.slug}</span>
                      <span
                        className={`shrink-0 rounded-full px-2 py-0.5 text-[11px] ${
                          audits.find((item) => item.slug === s.slug)?.status === 'error'
                            ? 'bg-rose-100 text-rose-700'
                            : audits.find((item) => item.slug === s.slug)?.status === 'warning'
                              ? 'bg-amber-100 text-amber-700'
                              : 'bg-emerald-100 text-emerald-700'
                        }`}
                      >
                        {audits.find((item) => item.slug === s.slug)?.status || '...'}
                      </span>
                    </div>
                    <div className="mt-1 truncate font-mono text-xs text-gray-400">{s.slug}</div>
                  </button>
                </li>
              ))}
              {skills.length === 0 ? (
                <li className="px-2.5 py-4 text-sm text-gray-400">暂无已接入技能</li>
              ) : null}
            </ul>
          </section>

          <div className="grid min-w-0 gap-4 xl:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
            <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-[0_16px_42px_rgba(15,23,42,0.06)]">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-gray-900">准入审核</p>
                  <p className="mt-1 text-xs text-gray-500">
                    检查新 skill 是否具备最基本的接管条件。
                  </p>
                </div>
                {selectedAudit ? (
                  <span className="rounded-full border border-gray-200 px-3 py-1 text-xs text-gray-700">
                    {selectedAudit.status}
                  </span>
                ) : null}
              </div>
              {!selectedAudit ? (
                <p className="mt-3 text-sm text-gray-400">选择左侧技能后查看审核结果。</p>
              ) : (
                <div className="mt-3 space-y-3 text-sm">
                  <div className="grid grid-cols-2 gap-2 text-xs text-gray-600">
                    <span className="rounded-xl border border-gray-100 bg-gray-50 px-3 py-2">
                      脚本入口：{selectedAudit.script_count}
                    </span>
                    <span className="rounded-xl border border-gray-100 bg-gray-50 px-3 py-2">
                      关联测试：{selectedAudit.test_count}
                    </span>
                    <span className="rounded-xl border border-gray-100 bg-gray-50 px-3 py-2">
                      触发条件：{selectedAudit.trigger_count}
                    </span>
                    <span className="rounded-xl border border-gray-100 bg-gray-50 px-3 py-2">
                      必备上下文：{selectedAudit.required_context_count}
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-2 text-xs font-medium">
                    <span className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-emerald-700">
                      SKILL.md：{selectedAudit.has_skill_md ? '已存在' : '缺失'}
                    </span>
                    <span className="rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-sky-700">
                      Workflow：{selectedAudit.has_workflow ? '已声明' : '缺失'}
                    </span>
                    <span className="rounded-full border border-violet-200 bg-violet-50 px-3 py-1 text-violet-700">
                      Safety：{selectedAudit.has_safety ? '已声明' : '缺失'}
                    </span>
                  </div>
                  <div>
                    <div className="mb-2 flex items-center justify-between gap-2">
                      <p className="text-xs font-semibold tracking-wide text-gray-500">审核问题</p>
                      {selectedAudit.issues.length > 3 ? (
                        <span className="text-[11px] text-gray-400">
                          先显示 {topIssues.length} 条，共 {selectedAudit.issues.length} 条
                        </span>
                      ) : null}
                    </div>
                    {selectedAudit.issues.length === 0 ? (
                      <p className="text-sm text-emerald-600">未发现明显缺口，可以继续接入候选集。</p>
                    ) : (
                      <ul className="space-y-2">
                        {topIssues.map((issue) => (
                          <li
                            key={`${issue.code}-${issue.message}`}
                            className="rounded-2xl border border-gray-100 bg-white px-3 py-2 shadow-[0_10px_28px_rgba(15,23,42,0.04)]"
                          >
                            <div className="text-xs font-semibold text-gray-800">
                              {issue.code} · {issue.level}
                            </div>
                            <div className="mt-1 text-gray-600">{issue.message}</div>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                </div>
              )}
            </section>

            <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-[0_16px_42px_rgba(15,23,42,0.06)]">
              <div className="mb-3 flex items-center justify-between">
                <span className="text-sm font-semibold text-gray-900">
                  {slug ? `已接入说明：${slug}` : '已接入说明'}
                </span>
              </div>
              {!slug ? (
                <p className="text-sm text-gray-400">选中技能后查看已接入说明。</p>
              ) : (
                <pre className="max-h-[calc(100vh-260px)] overflow-auto rounded-2xl border border-gray-100 bg-gray-50 p-4 font-mono text-xs text-gray-700">
                  {markdown}
                </pre>
              )}
            </section>
          </div>
        </div>
      </div>
    </div>
  );
}
