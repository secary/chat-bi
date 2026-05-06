import { useEffect, useState } from 'react';
import type { AdminSkillRow } from '../types/admin';
import {
  createSkillApi,
  deleteSkillApi,
  getSkillFile,
  listAdminSkills,
  patchSkillEnabled,
  putSkillFile,
} from '../api/client';
import { logger } from '../lib/logger';

export function SkillAdminPage() {
  const [skills, setSkills] = useState<AdminSkillRow[]>([]);
  const [slug, setSlug] = useState<string | null>(null);
  const [markdown, setMarkdown] = useState('');
  const [newSlug, setNewSlug] = useState('');
  const [busy, setBusy] = useState(false);

  const refresh = async () => {
    try {
      setSkills(await listAdminSkills());
    } catch (e) {
      logger.error('skills list', e);
    }
  };

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const s = await listAdminSkills();
        if (!cancelled) setSkills(s);
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

  const save = async () => {
    if (!slug) return;
    setBusy(true);
    try {
      await putSkillFile(slug, markdown);
      await refresh();
    } catch (e) {
      logger.error('save skill', e);
    } finally {
      setBusy(false);
    }
  };

  const toggle = async (s: AdminSkillRow) => {
    try {
      await patchSkillEnabled(s.slug, !s.enabled);
      await refresh();
    } catch (e) {
      logger.error('toggle skill', e);
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

  const remove = async () => {
    if (!slug) return;
    if (!window.confirm(`删除技能目录「${slug}」？`)) return;
    setBusy(true);
    try {
      await deleteSkillApi(slug);
      setSlug(null);
      setMarkdown('');
      await refresh();
    } catch (e) {
      logger.error('delete skill', e);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex h-full flex-col gap-4 overflow-auto p-6">
      <h2 className="text-lg font-semibold text-gray-900">技能管理</h2>
      <div className="flex flex-wrap gap-4">
        <div className="min-w-[240px] rounded-lg border border-gray-200 bg-white p-3">
          <p className="mb-2 text-xs font-medium text-gray-600">技能列表</p>
          <ul className="max-h-64 space-y-1 overflow-y-auto text-sm">
            {skills.map((s) => (
              <li key={s.slug} className="flex items-center gap-2">
                <button
                  type="button"
                  className={`flex-1 truncate rounded px-2 py-1 text-left hover:bg-gray-50 ${
                    slug === s.slug ? 'bg-gray-100 font-medium' : ''
                  }`}
                  onClick={() => void selectSkill(s.slug)}
                >
                  {s.name || s.slug}
                </button>
                <label className="flex items-center gap-1 text-xs text-gray-600">
                  <input
                    type="checkbox"
                    checked={s.enabled}
                    onChange={() => void toggle(s)}
                  />
                  启用
                </label>
              </li>
            ))}
          </ul>
          <div className="mt-3 flex gap-2 border-t border-gray-100 pt-3">
            <input
              className="flex-1 rounded border border-gray-300 px-2 py-1 text-xs"
              placeholder="新技能 slug"
              value={newSlug}
              onChange={(e) => setNewSlug(e.target.value)}
            />
            <button
              type="button"
              className="rounded bg-gray-900 px-2 py-1 text-xs text-white disabled:bg-gray-400"
              disabled={busy || !newSlug.trim()}
              onClick={() => void create()}
            >
              新建
            </button>
          </div>
        </div>

        <div className="min-h-[320px] min-w-[320px] flex-1 rounded-lg border border-gray-200 bg-white p-3">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-xs text-gray-600">
              {slug ? `编辑：${slug}` : '请选择左侧技能'}
            </span>
            <div className="flex gap-2">
              <button
                type="button"
                className="rounded border border-red-200 px-2 py-1 text-xs text-red-700 disabled:opacity-50"
                disabled={busy || !slug}
                onClick={() => void remove()}
              >
                删除
              </button>
              <button
                type="button"
                className="rounded bg-blue-600 px-3 py-1 text-xs text-white disabled:bg-gray-400"
                disabled={busy || !slug}
                onClick={() => void save()}
              >
                保存
              </button>
            </div>
          </div>
          <textarea
            className="h-[calc(100%-2rem)] min-h-[280px] w-full resize-none rounded border border-gray-300 p-2 font-mono text-xs"
            value={markdown}
            onChange={(e) => setMarkdown(e.target.value)}
            disabled={busy || !slug}
            spellCheck={false}
          />
        </div>
      </div>
    </div>
  );
}
