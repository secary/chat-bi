import { useEffect, useState } from 'react';
import { getLlmSettings, putLlmSettings } from '../api/client';
import type { LlmSettingsView } from '../types/admin';
import { logger } from '../lib/logger';
import { validateLlmConfig } from '../lib/llmConfigValidation';
import { detectPreset, LLM_PROVIDER_PRESETS } from '../lib/llmProviderPresets';

export function LlmConfigPage() {
  const [view, setView] = useState<LlmSettingsView | null>(null);
  const [model, setModel] = useState('');
  const [apiBase, setApiBase] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [error, setError] = useState('');
  const [saved, setSaved] = useState('');

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const v = await getLlmSettings();
        if (cancelled) return;
        setView(v);
        setModel(v.model ?? '');
        setApiBase(v.api_base ?? '');
        setApiKey('');
      } catch (e) {
        logger.error('llm settings', e);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const save = async () => {
    const vld = validateLlmConfig(model, apiBase);
    if (vld.errors.length > 0) {
      setSaved('');
      setError(vld.errors[0]);
      return;
    }
    try {
      setError('');
      const payload: { model?: string | null; api_base?: string | null; api_key?: string | null } =
        {
          model: model || null,
          api_base: apiBase || null,
        };
      if (apiKey.trim()) {
        payload.api_key = apiKey;
      }
      const v = await putLlmSettings(payload);
      setView(v);
      setApiKey('');
      setSaved('已保存。');
    } catch (e) {
      setSaved('');
      setError(e instanceof Error ? e.message : String(e));
      logger.error('save llm', e);
    }
  };

  const validation = validateLlmConfig(model, apiBase);
  const activePreset = detectPreset(model, apiBase);

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
      <p className="mb-4 max-w-xl text-sm text-gray-500">
        此处保存的配置会覆盖进程环境变量中的 `LLM_MODEL` / `API_BASE` / `OPENAI_API_KEY`（非空字段）。
        {view?.updated_at ? ` 最近更新：${String(view.updated_at)}` : ''}
      </p>
      <div className="mb-4 max-w-xl space-y-2 text-sm">
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-amber-800">
          使用 LiteLLM + OpenAI 兼容网关（`.../v1`）时，模型名请写成 `openai/&lt;具体模型名&gt;`。
        </div>
        {validation.warnings.map((w) => (
          <div key={w} className="rounded-lg border border-yellow-200 bg-yellow-50 px-3 py-2 text-yellow-800">
            {w}
          </div>
        ))}
        {(error || validation.errors.length > 0) && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-red-700">
            {error || validation.errors[0]}
          </div>
        )}
        {saved && <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-emerald-700">{saved}</div>}
      </div>
      <div className="max-w-xl space-y-3 rounded-xl border border-gray-200 bg-surface p-5 shadow-card text-sm">
        <div className="space-y-2">
          <div className="text-xs text-gray-500">厂商快捷配置（点击自动填充模型名与 API Base）</div>
          <div className="flex flex-wrap gap-2">
            {LLM_PROVIDER_PRESETS.map((preset) => {
              const active = activePreset === preset.id;
              return (
                <button
                  key={preset.id}
                  type="button"
                  onClick={() => {
                    setModel(preset.model);
                    setApiBase(preset.apiBase);
                    setSaved('');
                    setError('');
                  }}
                  className={
                    'rounded-full border px-3 py-1.5 text-xs transition-colors ' +
                    (active
                      ? 'border-emerald-300 bg-emerald-50 text-emerald-700'
                      : 'border-gray-200 bg-white text-gray-600 hover:bg-gray-50')
                  }
                  title={`${preset.model} @ ${preset.apiBase}`}
                >
                  {preset.label}
                </button>
              );
            })}
          </div>
        </div>
        <label className="block">
          模型名（如 openai/gpt-4o-mini）
          <input
            className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 transition-all focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
            value={model}
            onChange={(e) => setModel(e.target.value)}
          />
        </label>
        <label className="block">
          API Base（可选，兼容 OpenAI 网关）
          <input
            className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 transition-all focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
            value={apiBase}
            onChange={(e) => setApiBase(e.target.value)}
          />
        </label>
        <label className="block">
          API Key
          <input
            type="password"
            className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 transition-all focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
            value={apiKey}
            placeholder={view?.api_key_set ? '已配置，留空则不修改' : ''}
            onChange={(e) => setApiKey(e.target.value)}
          />
        </label>
        <button
          type="button"
          className="rounded-lg bg-accent px-4 py-2 text-sm text-white transition-colors hover:bg-accent-hover active:scale-[0.98] disabled:opacity-50"
          onClick={() => void save()}
          disabled={validation.errors.length > 0}
        >
          保存
        </button>
      </div>
    </div>
  );
}
