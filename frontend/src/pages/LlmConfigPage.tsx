import { useCallback, useEffect, useState } from 'react';
import {
  deleteLlmProfile,
  getLlmSettings,
  postLlmProfile,
  postLlmProfileProbe,
  postLlmProfileTest,
  putLlmProfile,
  putLlmProfilesActive,
} from '../api/client';
import type { LlmProfilePublic, LlmSettingsView } from '../types/admin';
import { logger } from '../lib/logger';

type SaveState = 'idle' | 'saving' | 'testing' | 'success' | 'error';
type ToastState = 'success' | 'error';
type LlmFormValidation = { ok: true } | { ok: false; message: string };

const ENV_DEFAULT_PROFILE_ID = 0;
const MASKED_API_KEY = '••••••••••••••••';
const DEFAULT_MODEL_PREFIX = 'openai/';
const MODEL_PREFIX_OPTIONS = ['openai/', 'anthropic/', 'gemini/', 'azure/', 'vertex_ai/', 'bedrock/'];

function findProfileForConfig(profiles: LlmProfilePublic[], model: string, apiBase: string) {
  const normalizedBase = apiBase.replace(/\/+$/, '');
  return profiles.find(
    (profile) =>
      !profile.is_env_default &&
      profile.model === model && (profile.api_base || '').replace(/\/+$/, '') === normalizedBase,
  );
}

function profileLabel(profile: LlmProfilePublic): string {
  return profile.display_name?.trim() || profile.model;
}

function splitModelName(model: string): { prefix: string; name: string } {
  const trimmed = model.trim();
  const slashIndex = trimmed.lastIndexOf('/');
  if (slashIndex < 0) {
    return { prefix: DEFAULT_MODEL_PREFIX, name: trimmed };
  }
  return {
    prefix: trimmed.slice(0, slashIndex + 1),
    name: trimmed.slice(slashIndex + 1),
  };
}

function normalizeModelPrefix(prefix: string): string {
  const trimmed = prefix.trim();
  if (!trimmed) return '';
  return trimmed.endsWith('/') ? trimmed : `${trimmed}/`;
}

function joinChineseList(items: string[]): string {
  if (items.length <= 1) return items[0] || '';
  return `${items.slice(0, -1).join('、')}和${items[items.length - 1]}`;
}

function validateApiBase(value: string): string | null {
  try {
    const parsed = new URL(value);
    if (!['http:', 'https:'].includes(parsed.protocol)) {
      return '请填写正确的 Base URL。';
    }
    if (!parsed.hostname.includes('.')) {
      return '请填写正确的 Base URL。';
    }
    return null;
  } catch {
    return '请填写正确的 Base URL。';
  }
}

function validateLlmForm(params: {
  modelPrefix: string;
  modelName: string;
  apiBase: string;
  apiKey: string;
  needsApiKey: boolean;
}): LlmFormValidation {
  const missing: string[] = [];
  if (!params.modelName.trim()) missing.push('模型名');
  if (!params.apiBase.trim()) missing.push('Base URL');
  if (params.needsApiKey && !params.apiKey.trim()) missing.push('API Key');
  if (missing.length) {
    return { ok: false, message: `请填写${joinChineseList(missing)}。` };
  }

  const normalizedPrefix = normalizeModelPrefix(params.modelPrefix);
  if (!normalizedPrefix) {
    return { ok: false, message: '请选择模型名前缀。' };
  }
  if (/\s/.test(params.modelName.trim())) {
    return { ok: false, message: '请填写正确的模型名。' };
  }

  const apiBaseError = validateApiBase(params.apiBase.trim());
  if (apiBaseError) return { ok: false, message: apiBaseError };

  if (params.needsApiKey) {
    const key = params.apiKey.trim();
    if (/\s/.test(key)) {
      return { ok: false, message: '请填写正确的 API Key。' };
    }
    if (key.length < 8) {
      return { ok: false, message: '请填写正确的 API Key。' };
    }
  }

  return { ok: true };
}

export function LlmConfigPage() {
  const [view, setView] = useState<LlmSettingsView | null>(null);
  const [displayName, setDisplayName] = useState('');
  const [modelPrefix, setModelPrefix] = useState(DEFAULT_MODEL_PREFIX);
  const [modelName, setModelName] = useState('');
  const [apiBase, setApiBase] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [state, setState] = useState<SaveState>('idle');
  const [message, setMessage] = useState('');
  const [toastState, setToastState] = useState<ToastState | null>(null);
  const [busyProfileId, setBusyProfileId] = useState<number | null>(null);
  const [activatingProfileId, setActivatingProfileId] = useState<number | null>(null);
  const [deletingProfileId, setDeletingProfileId] = useState<number | null>(null);
  const [editingProfileId, setEditingProfileId] = useState<number | null>(null);

  const profiles = view?.profiles ?? [];
  const selectedModelName = modelName.trim();
  const selectedModel = selectedModelName
    ? `${normalizeModelPrefix(modelPrefix)}${selectedModelName}`
    : '';
  const modelPrefixOptions = MODEL_PREFIX_OPTIONS.includes(modelPrefix)
    ? MODEL_PREFIX_OPTIONS
    : [...MODEL_PREFIX_OPTIONS, modelPrefix].filter(Boolean);
  const selectedApiBase = apiBase.trim();
  const activeProfileId =
    view?.active_profile_id ?? (view?.effective_source === 'env' ? ENV_DEFAULT_PROFILE_ID : null);
  const activeProfile = profiles.find((profile) => profile.id === activeProfileId);
  const activeModel = activeProfile?.model || view?.effective_model || '未配置';
  const editingProfile = profiles.find((profile) => profile.id === editingProfileId);

  const showOutcome = useCallback((nextState: ToastState, nextMessage: string) => {
    setState(nextState);
    setMessage(nextMessage);
    setToastState(nextState);
  }, []);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const next = await getLlmSettings();
        if (cancelled) return;
        setView(next);
      } catch (error) {
        if (cancelled) return;
        logger.error('llm settings', error);
        showOutcome('error', '读取配置失败，请稍后重试。');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [showOutcome]);

  useEffect(() => {
    if (!toastState) return undefined;
    const timer = window.setTimeout(() => {
      setToastState(null);
      if (toastState === 'success') {
        setMessage('');
        setState('idle');
      }
    }, 2600);
    return () => window.clearTimeout(timer);
  }, [toastState]);

  const refreshView = async () => {
    const next = await getLlmSettings();
    setView(next);
    return next;
  };

  const saveAndEnable = async () => {
    const needsApiKey = !editingProfileId;
    const validation = validateLlmForm({
      modelPrefix,
      modelName,
      apiBase,
      apiKey,
      needsApiKey,
    });
    if (!validation.ok) {
      showOutcome('error', validation.message);
      return;
    }
    setState('saving');
    setMessage('正在保存并测试连接...');
    setToastState(null);
    try {
      const probePayload = {
        model: selectedModel,
        api_base: selectedApiBase,
        api_key: apiKey.trim() || null,
        source_profile_id: editingProfileId,
      };
      const probe = await postLlmProfileProbe(probePayload);
      if (!probe.ok) {
        showOutcome('error', probe.message || '连接测试失败，未保存到已保存模型。');
        return;
      }
      const latest = await refreshView();
      const savedProfiles = latest.profiles ?? [];
      const existing = editingProfileId
        ? savedProfiles.find((profile) => profile.id === editingProfileId)
        : findProfileForConfig(savedProfiles, selectedModel, selectedApiBase);
      const payload = {
        display_name: displayName.trim() || selectedModel,
        model: probePayload.model,
        api_base: probePayload.api_base,
        api_key: apiKey.trim() || undefined,
      };
      const profileId = existing
        ? (await putLlmProfile(existing.id, payload)).profile.id
        : (await postLlmProfile(payload)).profile.id;
      await putLlmProfilesActive(profileId);
      const test = await postLlmProfileTest(profileId);
      await refreshView();
      setApiKey('');
      setEditingProfileId(null);
      if (test.ok) {
        showOutcome('success', `${payload.display_name} 已启用，连接测试通过。`);
      } else {
        showOutcome('error', test.message || '连接测试失败，请检查 API Key。');
      }
    } catch (error) {
      logger.error('simple llm setup', error);
      showOutcome('error', error instanceof Error ? error.message : '保存失败，请稍后重试。');
    }
  };

  const editProfile = (profile: LlmProfilePublic) => {
    if (profile.is_env_default) return;
    setEditingProfileId(profile.id);
    setDisplayName(profile.display_name || '');
    setApiKey('');
    const modelParts = splitModelName(profile.model);
    setModelPrefix(modelParts.prefix);
    setModelName(modelParts.name);
    setApiBase(profile.api_base || '');
    setState('idle');
    setMessage('已载入配置，将沿用已保存的 API Key 测试并保存。');
  };

  const activateProfile = async (profile: LlmProfilePublic) => {
    if (profile.id === activeProfileId) return;
    try {
      setActivatingProfileId(profile.id);
      await putLlmProfilesActive(profile.is_env_default ? null : profile.id);
      await refreshView();
      showOutcome('success', `${profileLabel(profile)} 已设为当前使用。`);
    } catch (error) {
      logger.error('activate llm profile', error);
      showOutcome('error', '启用失败，请稍后重试。');
    } finally {
      setActivatingProfileId(null);
    }
  };

  const testProfile = async (profile: LlmProfilePublic) => {
    try {
      setBusyProfileId(profile.id);
      const result = await postLlmProfileTest(profile.id);
      await refreshView();
      showOutcome(
        result.ok ? 'success' : 'error',
        result.ok ? `${profileLabel(profile)} 连接测试通过。` : result.message,
      );
    } catch (error) {
      logger.error('test llm profile', error);
      showOutcome('error', '测试失败，请稍后重试。');
    } finally {
      setBusyProfileId(null);
    }
  };

  const removeProfile = async (profile: LlmProfilePublic) => {
    if (profile.is_env_default) return;
    if (!window.confirm(`删除模型“${profileLabel(profile)}”？`)) return;
    try {
      setDeletingProfileId(profile.id);
      await deleteLlmProfile(profile.id);
      await refreshView();
      showOutcome('success', `${profileLabel(profile)} 已删除。`);
    } catch (error) {
      logger.error('delete llm profile', error);
      showOutcome('error', error instanceof Error ? error.message : '删除失败，请稍后重试。');
    } finally {
      setDeletingProfileId(null);
    }
  };

  return (
    <div className="h-full overflow-auto px-6 py-6 lg:px-8">
      <div className="mx-auto max-w-3xl">
        <div className="mb-6">
          <h2 className="text-lg font-semibold tracking-tight text-gray-900">LLM 配置</h2>
          <p className="mt-1 text-sm text-gray-500">填写模型名、Base URL、API Key 和备注，然后测试并启用。</p>
        </div>

        <section className="mb-5 rounded-lg border border-gray-200 bg-white p-4 shadow-card">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="text-xs text-gray-500">当前使用</div>
              <div className="mt-1 truncate text-base font-semibold text-gray-900">
                {activeProfile ? profileLabel(activeProfile) : view?.effective_model || '未配置'}
              </div>
              <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500">
                <span>模型：{activeModel}</span>
                <span>API Key：{view?.effective_api_key_set ? '已配置' : '未配置'}</span>
              </div>
            </div>
          </div>
        </section>

        {profiles.length > 0 ? (
          <section className="mb-5 rounded-lg border border-gray-200 bg-white p-4 shadow-card">
            <div className="mb-3 text-sm font-medium text-gray-900">已保存模型</div>
            <div className="flex flex-wrap gap-2" role="tablist" aria-label="已保存模型">
              {profiles.map((profile) => {
                const active = profile.id === activeProfileId;
                const envDefault = Boolean(profile.is_env_default);
                const busy = busyProfileId === profile.id;
                const activating = activatingProfileId === profile.id;
                const deleting = deletingProfileId === profile.id;
                const actionsDisabled =
                  busyProfileId !== null ||
                  activatingProfileId !== null ||
                  deletingProfileId !== null;
                const deleteDisabled = actionsDisabled || envDefault;
                return (
                  <div
                    key={profile.id}
                    role="tab"
                    aria-selected={active}
                    tabIndex={actionsDisabled ? -1 : 0}
                    onClick={() => {
                      if (!actionsDisabled) void activateProfile(profile);
                    }}
                    onKeyDown={(event) => {
                      if (actionsDisabled) return;
                      if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault();
                        void activateProfile(profile);
                      }
                    }}
                    className={
                      'flex min-w-[220px] cursor-pointer flex-col gap-2 rounded-lg border px-2.5 py-2 text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 ' +
                      (active ? 'border-accent bg-accent-light text-accent' : 'border-gray-200 bg-white text-gray-700')
                    }
                  >
                    <div className="flex items-center gap-2">
                      <div className="min-w-0 flex-1 truncate text-left font-medium">
                        {activating ? '切换中…' : profileLabel(profile)}
                      </div>
                      <button
                        type="button"
                        disabled={actionsDisabled || envDefault}
                        onClick={(event) => {
                          event.stopPropagation();
                          editProfile(profile);
                        }}
                        className={
                          'shrink-0 rounded border border-gray-200 bg-white px-2 py-0.5 text-xs text-gray-600 hover:bg-gray-50 disabled:opacity-50 ' +
                          (envDefault ? 'hidden' : '')
                        }
                      >
                        编辑
                      </button>
                      <button
                        type="button"
                        disabled={actionsDisabled}
                        onClick={(event) => {
                          event.stopPropagation();
                          void testProfile(profile);
                        }}
                        className="shrink-0 rounded border border-gray-200 bg-white px-2 py-0.5 text-xs text-gray-600 hover:bg-gray-50 disabled:opacity-50"
                      >
                        {busy ? '测试中…' : '测试'}
                      </button>
                      <button
                        type="button"
                        disabled={deleteDisabled}
                        onClick={(event) => {
                          event.stopPropagation();
                          void removeProfile(profile);
                        }}
                        className="shrink-0 rounded border border-red-100 bg-white px-2 py-0.5 text-xs text-red-600 hover:bg-red-50 disabled:opacity-50"
                        title={envDefault ? '默认配置不能删除' : '删除模型'}
                      >
                        {deleting ? '删除中…' : '删除'}
                      </button>
                    </div>
                    <div className="truncate text-xs text-gray-500">模型：{profile.model}</div>
                  </div>
                );
              })}
            </div>
          </section>
        ) : null}

        {message && state === 'error' ? (
          <div className="mb-5 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {message}
          </div>
        ) : null}

        <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-card">
          <div className="space-y-5">
            <label className="block text-sm font-medium text-gray-900">
              模型名
              <div className="mt-2 grid grid-cols-[minmax(92px,140px)_1fr] gap-2">
                <select
                  className="w-full rounded-lg border border-gray-200 px-3 py-2.5 text-sm transition-all focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30"
                  value={modelPrefix}
                  onChange={(event) => {
                    setModelPrefix(normalizeModelPrefix(event.target.value) || DEFAULT_MODEL_PREFIX);
                    setState('idle');
                    setMessage('');
                  }}
                >
                  {modelPrefixOptions.map((prefix) => (
                    <option key={prefix} value={prefix}>
                      {prefix}
                    </option>
                  ))}
                </select>
                <input
                  className="w-full min-w-0 rounded-lg border border-gray-200 px-3 py-2.5 text-sm transition-all focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30"
                  value={modelName}
                  onChange={(event) => {
                    const value = event.target.value.trimStart();
                    if (value.includes('/')) {
                      const modelParts = splitModelName(value);
                      setModelPrefix(modelParts.prefix);
                      setModelName(modelParts.name);
                    } else {
                      setModelName(value);
                    }
                    setState('idle');
                    setMessage('');
                  }}
                  placeholder="例如：doubao-seed-1-8-251228"
                />
              </div>
            </label>

            <label className="block text-sm font-medium text-gray-900">
              Base URL
              <input
                className="mt-2 w-full rounded-lg border border-gray-200 px-3 py-2.5 text-sm transition-all focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30"
                value={apiBase}
                onChange={(event) => {
                  setApiBase(event.target.value);
                  setState('idle');
                  setMessage('');
                }}
                placeholder="例如：https://api.example.com/v1"
              />
            </label>

            <label className="block text-sm font-medium text-gray-900">
              API Key
              <input
                type={editingProfileId ? 'text' : 'password'}
                className="mt-2 w-full rounded-lg border border-gray-200 px-3 py-2.5 text-sm transition-all focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30 disabled:bg-gray-50 disabled:text-gray-400"
                value={editingProfileId ? MASKED_API_KEY : apiKey}
                disabled={Boolean(editingProfileId)}
                onChange={(event) => {
                  setApiKey(event.target.value);
                  setState('idle');
                  setMessage('');
                }}
                placeholder={editingProfile?.api_key_set ? MASKED_API_KEY : '粘贴 API Key'}
              />
            </label>

            <label className="block text-sm font-medium text-gray-900">
              备注名{editingProfileId ? '（编辑中）' : ''}
              <input
                className="mt-2 w-full rounded-lg border border-gray-200 px-3 py-2.5 text-sm transition-all focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30"
                value={displayName}
                onChange={(event) => setDisplayName(event.target.value)}
                placeholder={selectedModel || '默认使用模型名'}
              />
            </label>

            <button
              type="button"
              onClick={() => void saveAndEnable()}
              disabled={state === 'saving'}
              className="w-full rounded-lg bg-accent px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-accent-hover disabled:opacity-50 sm:w-auto"
            >
              {state === 'saving' ? '测试中…' : editingProfileId ? '测试并保存' : '测试并启用'}
            </button>
            {editingProfileId ? (
              <button
                type="button"
                onClick={() => {
                  setEditingProfileId(null);
                  setDisplayName('');
                  setModelPrefix(DEFAULT_MODEL_PREFIX);
                  setModelName('');
                  setApiBase('');
                  setApiKey('');
                  setState('idle');
                  setMessage('');
                }}
                className="w-full rounded-lg border border-gray-200 px-4 py-2.5 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 sm:ml-2 sm:w-auto"
              >
                取消编辑
              </button>
            ) : null}
          </div>
        </section>
      </div>
      {toastState ? (
        <div className="pointer-events-none fixed inset-0 z-50 flex items-center justify-center px-4">
          <div
            className={
              'max-w-md rounded-lg border px-5 py-3 text-sm font-medium shadow-lg ' +
              (toastState === 'success'
                ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                : 'border-red-200 bg-red-50 text-red-700')
            }
          >
            {toastState === 'success' ? '配置成功' : '配置失败'}
          </div>
        </div>
      ) : null}
    </div>
  );
}
