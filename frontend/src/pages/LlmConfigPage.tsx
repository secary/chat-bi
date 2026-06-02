import { useEffect, useMemo, useState } from 'react';
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
import { detectPreset, LLM_PROVIDER_PRESETS } from '../lib/llmProviderPresets';

type SaveState = 'idle' | 'saving' | 'testing' | 'success' | 'error';

const CUSTOM_PROVIDER_ID = 'other';
const PROVIDER_OPTIONS = [...LLM_PROVIDER_PRESETS, { id: CUSTOM_PROVIDER_ID, label: '其他' }];
const MASKED_API_KEY = '••••••••••••••••';

function findProfileForPreset(profiles: LlmProfilePublic[], model: string, apiBase: string) {
  const normalizedBase = apiBase.replace(/\/+$/, '');
  return profiles.find(
    (profile) =>
      profile.model === model && (profile.api_base || '').replace(/\/+$/, '') === normalizedBase,
  );
}

function profileLabel(profile: LlmProfilePublic): string {
  return profile.display_name?.trim() || profile.model;
}

export function LlmConfigPage() {
  const [view, setView] = useState<LlmSettingsView | null>(null);
  const [providerId, setProviderId] = useState(LLM_PROVIDER_PRESETS[0]?.id ?? '');
  const [displayName, setDisplayName] = useState('');
  const [modelName, setModelName] = useState(LLM_PROVIDER_PRESETS[0]?.model ?? '');
  const [customApiBase, setCustomApiBase] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [state, setState] = useState<SaveState>('idle');
  const [message, setMessage] = useState('');
  const [busyProfileId, setBusyProfileId] = useState<number | null>(null);
  const [activatingProfileId, setActivatingProfileId] = useState<number | null>(null);
  const [deletingProfileId, setDeletingProfileId] = useState<number | null>(null);
  const [editingProfileId, setEditingProfileId] = useState<number | null>(null);

  const profiles = view?.profiles ?? [];
  const preset = useMemo(
    () => LLM_PROVIDER_PRESETS.find((item) => item.id === providerId) ?? null,
    [providerId],
  );
  const customProviderSelected = providerId === CUSTOM_PROVIDER_ID;
  const selectedModel = modelName.trim();
  const selectedApiBase = customProviderSelected ? customApiBase.trim() : preset?.apiBase || '';
  const activeProfile = profiles.find((profile) => profile.id === view?.active_profile_id);
  const activeModel = activeProfile?.model || view?.effective_model || '未配置';
  const editingProfile = profiles.find((profile) => profile.id === editingProfileId);

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
        setState('error');
        setMessage('读取配置失败，请稍后重试。');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const refreshView = async () => {
    const next = await getLlmSettings();
    setView(next);
    return next;
  };

  const saveAndEnable = async () => {
    const needsApiKey = !editingProfileId;
    if (!selectedModel || !selectedApiBase || (needsApiKey && !apiKey.trim())) {
      setState('error');
      setMessage(customProviderSelected ? '请填写模型名、Base URL 和 API Key。' : '请填写模型名和 API Key。');
      return;
    }
    setState('saving');
    setMessage('正在保存并测试连接...');
    try {
      const probePayload = {
        model: selectedModel,
        api_base: selectedApiBase,
        api_key: apiKey.trim() || null,
        source_profile_id: editingProfileId,
      };
      const probe = await postLlmProfileProbe(probePayload);
      if (!probe.ok) {
        setState('error');
        setMessage(probe.message || '连接测试失败，未保存到已保存模型。');
        return;
      }
      const latest = await refreshView();
      const savedProfiles = latest.profiles ?? [];
      const existing = editingProfileId
        ? savedProfiles.find((profile) => profile.id === editingProfileId)
        : findProfileForPreset(savedProfiles, selectedModel, selectedApiBase);
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
        setState('success');
        setMessage(`${payload.display_name} 已启用，连接测试通过。`);
      } else {
        setState('error');
        setMessage(test.message || '连接测试失败，请检查 API Key。');
      }
    } catch (error) {
      logger.error('simple llm setup', error);
      setState('error');
      setMessage(error instanceof Error ? error.message : '保存失败，请稍后重试。');
    }
  };

  const editProfile = (profile: LlmProfilePublic) => {
    const detectedProviderId = detectPreset(profile.model, profile.api_base || '');
    setEditingProfileId(profile.id);
    setDisplayName(profile.display_name || '');
    setApiKey('');
    if (detectedProviderId) {
      setProviderId(detectedProviderId);
      setModelName(profile.model);
      setCustomApiBase('');
    } else {
      setProviderId(CUSTOM_PROVIDER_ID);
      setModelName(profile.model);
      setCustomApiBase(profile.api_base || '');
    }
    setState('idle');
    setMessage('已载入配置，将沿用已保存的 API Key 测试并保存。');
  };

  const activateProfile = async (profile: LlmProfilePublic) => {
    if (profile.id === view?.active_profile_id) return;
    try {
      setActivatingProfileId(profile.id);
      await putLlmProfilesActive(profile.id);
      await refreshView();
      setState('success');
      setMessage(`${profileLabel(profile)} 已设为当前使用。`);
    } catch (error) {
      logger.error('activate llm profile', error);
      setState('error');
      setMessage('启用失败，请稍后重试。');
    } finally {
      setActivatingProfileId(null);
    }
  };

  const testProfile = async (profile: LlmProfilePublic) => {
    try {
      setBusyProfileId(profile.id);
      const result = await postLlmProfileTest(profile.id);
      await refreshView();
      setState(result.ok ? 'success' : 'error');
      setMessage(result.ok ? `${profileLabel(profile)} 连接测试通过。` : result.message);
    } catch (error) {
      logger.error('test llm profile', error);
      setState('error');
      setMessage('测试失败，请稍后重试。');
    } finally {
      setBusyProfileId(null);
    }
  };

  const removeProfile = async (profile: LlmProfilePublic) => {
    if (profile.id === view?.active_profile_id && profiles.length <= 1) {
      setState('error');
      setMessage('当前配置是唯一可用模型，不能删除。');
      return;
    }
    if (!window.confirm(`删除模型“${profileLabel(profile)}”？`)) return;
    try {
      setDeletingProfileId(profile.id);
      await deleteLlmProfile(profile.id);
      await refreshView();
      setState('success');
      setMessage(`${profileLabel(profile)} 已删除。`);
    } catch (error) {
      logger.error('delete llm profile', error);
      setState('error');
      setMessage(error instanceof Error ? error.message : '删除失败，请稍后重试。');
    } finally {
      setDeletingProfileId(null);
    }
  };

  return (
    <div className="h-full overflow-auto px-6 py-6 lg:px-8">
      <div className="mx-auto max-w-3xl">
        <div className="mb-6">
          <h2 className="text-lg font-semibold tracking-tight text-gray-900">LLM 配置</h2>
          <p className="mt-1 text-sm text-gray-500">选择厂商，填入 API Key，然后测试并启用。</p>
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
                const active = profile.id === view?.active_profile_id;
                const busy = busyProfileId === profile.id;
                const activating = activatingProfileId === profile.id;
                const deleting = deletingProfileId === profile.id;
                const actionsDisabled =
                  busyProfileId !== null ||
                  activatingProfileId !== null ||
                  deletingProfileId !== null;
                const deleteDisabled = actionsDisabled || (active && profiles.length <= 1);
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
                        disabled={actionsDisabled}
                        onClick={(event) => {
                          event.stopPropagation();
                          editProfile(profile);
                        }}
                        className="shrink-0 rounded border border-gray-200 bg-white px-2 py-0.5 text-xs text-gray-600 hover:bg-gray-50 disabled:opacity-50"
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
                        title={active && profiles.length <= 1 ? '当前配置是唯一可用模型，不能删除' : '删除模型'}
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

        <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-card">
          <div className="space-y-5">
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-900">选择厂商</label>
              <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                {PROVIDER_OPTIONS.map((item) => {
                  const selected = item.id === providerId;
                  return (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => {
                        setProviderId(item.id);
                        const selectedPreset = LLM_PROVIDER_PRESETS.find(
                          (candidate) => candidate.id === item.id,
                        );
                        setModelName(selectedPreset?.model || '');
                        if (selectedPreset) setCustomApiBase('');
                        setState('idle');
                        setMessage('');
                      }}
                      className={
                        'rounded-lg border px-3 py-3 text-left text-sm transition-colors ' +
                        (selected
                          ? 'border-accent bg-accent-light text-accent'
                          : 'border-gray-200 bg-white text-gray-700 hover:bg-gray-50')
                      }
                    >
                      <div className="font-medium">{item.label}</div>
                    </button>
                  );
                })}
              </div>
            </div>

            <label className="block text-sm font-medium text-gray-900">
              模型名
              <input
                className="mt-2 w-full rounded-lg border border-gray-200 px-3 py-2.5 text-sm transition-all focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30"
                value={modelName}
                onChange={(event) => {
                  setModelName(event.target.value);
                  setState('idle');
                  setMessage('');
                }}
                placeholder="例如：openai/gpt-4o-mini"
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

            {customProviderSelected ? (
              <div>
                <label className="block text-sm font-medium text-gray-900">
                  Base URL
                  <input
                    className="mt-2 w-full rounded-lg border border-gray-200 px-3 py-2.5 text-sm transition-all focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30"
                    value={customApiBase}
                    onChange={(event) => {
                      setCustomApiBase(event.target.value);
                      setState('idle');
                      setMessage('');
                    }}
                    placeholder="例如：https://api.example.com/v1"
                  />
                </label>
              </div>
            ) : null}

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
                placeholder={editingProfile?.api_key_set ? MASKED_API_KEY : '粘贴厂商控制台生成的 API Key'}
              />
            </label>

            {message ? (
              <div
                className={
                  'rounded-lg border px-3 py-2 text-sm ' +
                  (state === 'success'
                    ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                    : state === 'error'
                      ? 'border-red-200 bg-red-50 text-red-700'
                      : 'border-gray-200 bg-gray-50 text-gray-600')
                }
              >
                {message}
              </div>
            ) : null}

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
                  setModelName(preset?.model || '');
                  setCustomApiBase('');
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
    </div>
  );
}
