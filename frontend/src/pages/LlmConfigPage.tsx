import { useCallback, useEffect, useState } from 'react';
import {
  deleteLlmProfile,
  getLlmSettings,
  postLlmProfile,
  postLlmProfileTest,
  postLlmProfilesTestAll,
  putLlmProfile,
  putLlmProfilesActive,
  putLlmProfilesReorder,
} from '../api/client';
import type { LlmProfilePublic, LlmSettingsView } from '../types/admin';
import { logger } from '../lib/logger';
import { validateLlmConfig } from '../lib/llmConfigValidation';
import { LlmProfileList } from '../components/LlmProfileList';
import { LlmConfigEditorCard } from '../components/LlmConfigEditorCard';

function profileToForm(p: LlmProfilePublic) {
  return {
    displayName: p.display_name ?? '',
    model: p.model ?? '',
    apiBase: p.api_base ?? '',
    apiKey: '',
  };
}

export function LlmConfigPage() {
  const [view, setView] = useState<LlmSettingsView | null>(null);
  const [displayName, setDisplayName] = useState('');
  const [model, setModel] = useState('');
  const [apiBase, setApiBase] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [error, setError] = useState('');
  const [saved, setSaved] = useState('');
  const [selectedKey, setSelectedKey] = useState<number | 'new'>('new');
  const [busyTest, setBusyTest] = useState<'all' | number | null>(null);

  const profiles = view?.profiles ?? [];
  const activeProfileId =
    view?.active_profile_id !== undefined ? view.active_profile_id : null;

  const refreshView = useCallback(async () => {
    const v = await getLlmSettings();
    setView(v);
    return v;
  }, []);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const v = await getLlmSettings();
        if (cancelled) return;
        setView(v);
        const list = v.profiles ?? [];
        if (list.length > 0) {
          const pref = v.active_profile_id ?? list[0]?.id;
          if (pref !== undefined && pref !== null) {
            const match = list.find((p) => p.id === pref);
            if (match) {
              setSelectedKey(pref);
              const f = profileToForm(match);
              setDisplayName(f.displayName);
              setModel(f.model);
              setApiBase(f.apiBase);
              setApiKey('');
              return;
            }
          }
        }
        setSelectedKey('new');
        setDisplayName('');
        setModel('');
        setApiBase('');
        setApiKey('');
      } catch (e) {
        logger.error('llm settings', e);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const applySelection = (id: number) => {
    const p = profiles.find((x) => x.id === id);
    if (!p) return;
    setSelectedKey(id);
    const f = profileToForm(p);
    setDisplayName(f.displayName);
    setModel(f.model);
    setApiBase(f.apiBase);
    setApiKey('');
    setSaved('');
    setError('');
  };

  const save = async () => {
    const vld = validateLlmConfig(model, apiBase);
    if (vld.errors.length > 0) {
      setSaved('');
      setError(vld.errors[0]);
      return;
    }
    try {
      setError('');
      if (selectedKey === 'new') {
        const payload: Parameters<typeof postLlmProfile>[0] = {
          display_name: displayName.trim() || null,
          model: model.trim(),
          api_base: apiBase.trim() || null,
        };
        if (apiKey.trim()) payload.api_key = apiKey.trim();
        await postLlmProfile(payload);
      } else {
        const payload: Parameters<typeof putLlmProfile>[1] = {
          display_name: displayName.trim() || null,
          model: model.trim(),
          api_base: apiBase.trim() || null,
        };
        if (apiKey.trim()) payload.api_key = apiKey.trim();
        await putLlmProfile(selectedKey, payload);
      }
      const v = await refreshView();
      setApiKey('');
      setSaved('已保存。');
      const list = v.profiles ?? [];
      if (selectedKey === 'new' && list.length > 0) {
        const last = list[list.length - 1];
        if (last) applySelection(last.id);
      }
    } catch (e) {
      setSaved('');
      setError(e instanceof Error ? e.message : String(e));
      logger.error('save llm profile', e);
    }
  };

  const move = async (id: number, dir: 'up' | 'down') => {
    const ids = profiles.map((p) => p.id);
    const i = ids.indexOf(id);
    if (i < 0) return;
    const j = dir === 'up' ? i - 1 : i + 1;
    if (j < 0 || j >= ids.length) return;
    const next = [...ids];
    [next[i], next[j]] = [next[j], next[i]];
    try {
      await putLlmProfilesReorder(next);
      await refreshView();
    } catch (e) {
      logger.error('reorder llm profiles', e);
    }
  };

  const activate = async (id: number) => {
    try {
      await putLlmProfilesActive(id);
      await refreshView();
    } catch (e) {
      logger.error('set active llm profile', e);
    }
  };

  const runTest = async (id: number) => {
    try {
      setBusyTest(id);
      await postLlmProfileTest(id);
      await refreshView();
    } catch (e) {
      logger.error('test llm profile', e);
    } finally {
      setBusyTest(null);
    }
  };

  const runTestAll = async () => {
    try {
      setBusyTest('all');
      await postLlmProfilesTestAll();
      await refreshView();
    } catch (e) {
      logger.error('test all llm profiles', e);
    } finally {
      setBusyTest(null);
    }
  };

  const remove = async (id: number) => {
    try {
      await deleteLlmProfile(id);
      const v = await refreshView();
      const list = v.profiles ?? [];
      if (selectedKey === id) {
        if (list.length > 0 && list[0]) {
          applySelection(list[0].id);
        } else {
          setSelectedKey('new');
          setDisplayName('');
          setModel('');
          setApiBase('');
          setApiKey('');
        }
      }
    } catch (e) {
      logger.error('delete llm profile', e);
    }
  };

  return (
    <div className="h-full overflow-auto p-6 lg:p-8">
      <h2 className="mb-4 text-lg font-semibold tracking-tight text-gray-900">LLM 配置</h2>
      <div className="mb-4 max-w-xl rounded-xl border border-accent/20 bg-accent-light p-3.5 text-sm text-accent">
        当前生效模型：
        <span className="ml-1 font-medium">{view?.effective_model || '未配置'}</span>
        <span className="ml-2 text-xs text-accent/70">
          来源：{view?.effective_source === 'saved_settings' ? '管理页配置' : '环境变量'}
        </span>
        {view?.effective_api_base && (
          <div className="mt-1 text-xs text-accent/80">API Base：{view.effective_api_base}</div>
        )}
        <div className="mt-1 text-xs text-accent/80">
          API Key：{view?.effective_api_key_set ? '已配置' : '未配置'}
        </div>
      </div>
      <p className="mb-4 max-w-4xl text-xs text-gray-500">
        保存多条模型后，右侧可切换「对话默认」；请求失败时会按列表顺序（当前选用优先，其余从上到下）自动尝试其它模型。
      </p>
      <div className="grid max-w-6xl gap-8 lg:grid-cols-[1fr_340px]">
        <div>
          <p className="mb-4 text-sm text-gray-500">
            此处保存的配置会覆盖进程环境变量中的 `LLM_MODEL` / `API_BASE` / `OPENAI_API_KEY`（非空字段）。
            {view?.updated_at ? ` 最近更新：${String(view.updated_at)}` : ''}
          </p>
          <LlmConfigEditorCard
            displayName={displayName}
            setDisplayName={setDisplayName}
            model={model}
            setModel={setModel}
            apiBase={apiBase}
            setApiBase={setApiBase}
            apiKey={apiKey}
            setApiKey={setApiKey}
            selectedKey={selectedKey}
            profiles={profiles}
            saved={saved}
            error={error}
            setSaved={setSaved}
            setError={setError}
            onSave={save}
            onNewBlank={() => {
              setSelectedKey('new');
              setDisplayName('');
              setModel('');
              setApiBase('');
              setApiKey('');
              setSaved('');
              setError('');
            }}
          />
        </div>
        <aside className="lg:border-l lg:border-gray-100 lg:pl-8">
          <LlmProfileList
            profiles={profiles}
            activeProfileId={activeProfileId ?? null}
            selectedKey={selectedKey}
            busyTest={busyTest}
            onSelect={(id) => applySelection(id)}
            onSelectNew={() => {
              setSelectedKey('new');
              setDisplayName('');
              setModel('');
              setApiBase('');
              setApiKey('');
              setSaved('');
              setError('');
            }}
            onActivate={(id) => void activate(id)}
            onDelete={(id) => void remove(id)}
            onTest={(id) => void runTest(id)}
            onTestAll={() => void runTestAll()}
            onMove={(id, dir) => void move(id, dir)}
          />
        </aside>
      </div>
    </div>
  );
}
