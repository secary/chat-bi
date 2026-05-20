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
    <div className="flex h-full flex-col gap-4 overflow-auto p-6 lg:p-8">
      <div>
        <h2 className="text-lg font-semibold tracking-tight text-gray-900">技能接入</h2>
        <p className="mt-1 text-xs text-gray-500">
          只保留新能力接入与审核，不承载日常技能运维。
        </p>
      </div>
      <div className="grid gap-4 xl:grid-cols-[320px_minmax(0,1fr)]">
        <div className="space-y-4">
          <div className="rounded-xl border border-gray-200 bg-surface p-4 shadow-card">
            <p className="text-sm font-semibold text-gray-900">新技能接入</p>
            <p className="mt-1 text-xs text-gray-500">
              创建接入项后，补充说明与脚本，再看审核结果。
            </p>
            <div className="mt-3 flex gap-2">
              <input
                className="flex-1 rounded-lg border border-gray-200 px-3 py-2 text-xs transition-all focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30"
                placeholder="新技能 slug"
                value={newSlug}
                onChange={(e) => setNewSlug(e.target.value)}
              />
              <button
                type="button"
                className="whitespace-nowrap rounded-lg bg-accent px-3 py-2 text-xs text-white transition-colors hover:bg-accent-hover disabled:opacity-50"
                disabled={busy || !newSlug.trim()}
                onClick={() => void create()}
              >
                创建接入项
              </button>
            </div>
            <div className="mt-3 flex flex-wrap gap-2 text-xs text-gray-600">
              <span className="rounded-full border border-gray-200 px-3 py-1">可直接纳入 {readyCount}</span>
              <span className="rounded-full border border-gray-200 px-3 py-1">待补信息 {warningCount}</span>
              <span className="rounded-full border border-gray-200 px-3 py-1">阻塞缺口 {errorCount}</span>
            </div>
          </div>

          <div className="rounded-xl border border-gray-200 bg-surface p-3 shadow-card">
            <p className="mb-2 text-xs font-medium tracking-wide text-gray-500">已接入技能概览</p>
            <ul className="max-h-[420px] space-y-1 overflow-y-auto text-sm">
            {skills.map((s) => (
              <li key={s.slug}>
                <button
                  type="button"
                  className={`w-full truncate rounded-lg px-2.5 py-1.5 text-left transition-colors hover:bg-gray-50 ${
                    slug === s.slug ? 'bg-gray-100 font-medium text-gray-900' : ''
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
                </button>
              </li>
            ))}
            </ul>
          </div>
        </div>

        <div className="space-y-4">
          <div className="rounded-xl border border-gray-200 bg-surface p-4 shadow-card">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-gray-900">准入审核</p>
                <p className="mt-1 text-xs text-gray-500">
                  检查新 skill 是否具备最基本的接管条件。
                </p>
              </div>
              {selectedAudit ? (
                <span className="rounded-full bg-gray-100 px-3 py-1 text-xs text-gray-700">
                  {selectedAudit.status}
                </span>
              ) : null}
            </div>
            {!selectedAudit ? (
              <p className="mt-3 text-sm text-gray-400">选择左侧技能后查看审核结果。</p>
            ) : (
              <div className="mt-3 space-y-3 text-sm">
                <div className="flex flex-wrap gap-2 text-xs text-gray-600">
                  <span className="rounded-full border border-gray-200 px-3 py-1">
                    脚本入口：{selectedAudit.script_count}
                  </span>
                  <span className="rounded-full border border-gray-200 px-3 py-1">
                    关联测试：{selectedAudit.test_count}
                  </span>
                  <span className="rounded-full border border-gray-200 px-3 py-1">
                    触发条件：{selectedAudit.trigger_count}
                  </span>
                  <span className="rounded-full border border-gray-200 px-3 py-1">
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
                          className="rounded-lg border border-gray-100 px-3 py-2"
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
          </div>

          <div className="rounded-xl border border-gray-200 bg-surface p-3 shadow-card">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-xs text-gray-500">
                {slug ? `已接入说明：${slug}` : '请选择左侧技能'}
              </span>
            </div>
            <p className="mb-3 text-xs text-gray-500">
              这里保留已接入 skill 的说明展示，便于查看接入背景与审核元数据。
            </p>
            {!slug ? (
              <p className="text-sm text-gray-400">选中技能后查看已接入说明。</p>
            ) : (
              <pre className="max-h-[420px] overflow-auto rounded-lg border border-gray-200 bg-gray-50 p-3 font-mono text-xs text-gray-700">
                {markdown}
              </pre>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
