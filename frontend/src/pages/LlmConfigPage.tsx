import { useEffect, useMemo, useState } from 'react';
import {
  getLlmSettings,
  postLlmProfile,
  postLlmProfileTest,
  putLlmProfile,
  putLlmProfilesActive,
} from '../api/client';
import type { LlmProfilePublic, LlmSettingsView } from '../types/admin';
import { logger } from '../lib/logger';
import { LLM_PROVIDER_PRESETS } from '../lib/llmProviderPresets';

type SaveState = 'idle' | 'saving' | 'testing' | 'success' | 'error';

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

function statusText(status: string): string {
  if (status === 'ok') return '可用';
  if (status === 'error') return '连接失败';
  return '未检测';
}

function statusClass(status: string): string {
  if (status === 'ok') return 'border-emerald-200 bg-emerald-50 text-emerald-700';
  if (status === 'error') return 'border-red-200 bg-red-50 text-red-700';
  return 'border-gray-200 bg-gray-50 text-gray-600';
}

export function LlmConfigPage() {
  const [view, setView] = useState<LlmSettingsView | null>(null);
  const [providerId, setProviderId] = useState(LLM_PROVIDER_PRESETS[0]?.id ?? '');
  const [displayName, setDisplayName] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [state, setState] = useState<SaveState>('idle');
  const [message, setMessage] = useState('');
  const [busyProfileId, setBusyProfileId] = useState<number | null>(null);

  const profiles = view?.profiles ?? [];
  const preset = useMemo(
    () => LLM_PROVIDER_PRESETS.find((item) => item.id === providerId) ?? LLM_PROVIDER_PRESETS[0],
    [providerId],
  );
  const effectiveSource = view?.effective_source === 'saved_settings' ? '管理页配置' : '环境变量';
  const activeProfile = profiles.find((profile) => profile.id === view?.active_profile_id);
  const activeStatus = activeProfile?.health_status || 'unknown';

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
    if (!preset || !apiKey.trim()) {
      setState('error');
      setMessage('请选择厂商并填写 API Key。');
      return;
    }
    setState('saving');
    setMessage('正在保存并测试连接...');
    try {
      const latest = await refreshView();
      const existing = findProfileForPreset(latest.profiles ?? [], preset.model, preset.apiBase);
      const payload = {
        display_name: displayName.trim() || preset.label,
        model: preset.model,
        api_base: preset.apiBase,
        api_key: apiKey.trim(),
      };
      const profileId = existing
        ? (await putLlmProfile(existing.id, payload)).profile.id
        : (await postLlmProfile(payload)).profile.id;
      await putLlmProfilesActive(profileId);
      const test = await postLlmProfileTest(profileId);
      await refreshView();
      setApiKey('');
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

  const activateProfile = async (profile: LlmProfilePublic) => {
    try {
      setBusyProfileId(profile.id);
      await putLlmProfilesActive(profile.id);
      await refreshView();
      setState('success');
      setMessage(`${profileLabel(profile)} 已设为当前使用。`);
    } catch (error) {
      logger.error('activate llm profile', error);
      setState('error');
      setMessage('启用失败，请稍后重试。');
    } finally {
      setBusyProfileId(null);
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
                <span>来源：{effectiveSource}</span>
                <span>API Key：{view?.effective_api_key_set ? '已配置' : '未配置'}</span>
              </div>
            </div>
            <span className={`rounded-full border px-2.5 py-1 text-xs ${statusClass(activeStatus)}`}>
              {statusText(activeStatus)}
            </span>
          </div>
        </section>

        {profiles.length > 0 ? (
          <section className="mb-5 rounded-lg border border-gray-200 bg-white p-4 shadow-card">
            <div className="mb-3 text-sm font-medium text-gray-900">已保存模型</div>
            <div className="flex flex-wrap gap-2">
              {profiles.map((profile) => {
                const active = profile.id === view?.active_profile_id;
                const busy = busyProfileId === profile.id;
                return (
                  <div
                    key={profile.id}
                    className={
                      'flex items-center gap-2 rounded-lg border px-2.5 py-2 text-sm ' +
                      (active ? 'border-accent bg-accent-light text-accent' : 'border-gray-200 bg-white text-gray-700')
                    }
                  >
                    <button type="button" onClick={() => void activateProfile(profile)} className="max-w-[180px] truncate font-medium">
                      {profileLabel(profile)}
                    </button>
                    <span className={`rounded-full border px-1.5 py-0.5 text-[10px] ${statusClass(profile.health_status || 'unknown')}`}>
                      {statusText(profile.health_status || 'unknown')}
                    </span>
                    <button
                      type="button"
                      disabled={busyProfileId !== null}
                      onClick={() => void testProfile(profile)}
                      className="rounded border border-gray-200 bg-white px-2 py-0.5 text-xs text-gray-600 hover:bg-gray-50 disabled:opacity-50"
                    >
                      {busy ? '测试中…' : '测试'}
                    </button>
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
                {LLM_PROVIDER_PRESETS.map((item) => {
                  const selected = item.id === providerId;
                  return (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => {
                        setProviderId(item.id);
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
              备注名
              <input
                className="mt-2 w-full rounded-lg border border-gray-200 px-3 py-2.5 text-sm transition-all focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30"
                value={displayName}
                onChange={(event) => setDisplayName(event.target.value)}
                placeholder={preset ? `${preset.label} 默认模型` : '便于识别，例如：生产 MiniMax'}
              />
            </label>

            <label className="block text-sm font-medium text-gray-900">
              API Key
              <input
                type="password"
                className="mt-2 w-full rounded-lg border border-gray-200 px-3 py-2.5 text-sm transition-all focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30"
                value={apiKey}
                onChange={(event) => {
                  setApiKey(event.target.value);
                  setState('idle');
                  setMessage('');
                }}
                placeholder="粘贴厂商控制台生成的 API Key"
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
              {state === 'saving' ? '测试中…' : '测试并启用'}
            </button>
          </div>
        </section>
      </div>
    </div>
  );
}
