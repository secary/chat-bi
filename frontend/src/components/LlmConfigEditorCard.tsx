import type { LlmProfilePublic } from '../types/admin';
import { validateLlmConfig } from '../lib/llmConfigValidation';
import { detectPreset, LLM_PROVIDER_PRESETS } from '../lib/llmProviderPresets';

export interface LlmConfigEditorCardProps {
  displayName: string;
  setDisplayName: (v: string) => void;
  model: string;
  setModel: (v: string) => void;
  apiBase: string;
  setApiBase: (v: string) => void;
  apiKey: string;
  setApiKey: (v: string) => void;
  selectedKey: number | 'new';
  profiles: LlmProfilePublic[];
  saved: string;
  error: string;
  setSaved: (v: string) => void;
  setError: (v: string) => void;
  onSave: () => void;
  onNewBlank: () => void;
}

export function LlmConfigEditorCard({
  displayName,
  setDisplayName,
  model,
  setModel,
  apiBase,
  setApiBase,
  apiKey,
  setApiKey,
  selectedKey,
  profiles,
  saved,
  error,
  setSaved,
  setError,
  onSave,
  onNewBlank,
}: LlmConfigEditorCardProps) {
  const validation = validateLlmConfig(model, apiBase);
  const activePreset = detectPreset(model, apiBase);
  const activePresetMeta = LLM_PROVIDER_PRESETS.find((preset) => preset.id === activePreset) || null;

  return (
    <>
      <div className="mb-4 space-y-2 text-sm">
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
        {saved && (
          <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-emerald-700">{saved}</div>
        )}
      </div>
      <div className="space-y-3 rounded-xl border border-gray-200 bg-surface p-5 shadow-card text-sm">
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
          {activePresetMeta ? (
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-800">
              <div className="font-medium">{activePresetMeta.label} 推荐配置</div>
              <div className="mt-1">{activePresetMeta.modelRule}</div>
              <div className="mt-1">{activePresetMeta.note}</div>
            </div>
          ) : (
            <div className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-xs text-gray-600">
              当前输入未命中预设，建议先点击上方厂商按钮再补充 API Key。
            </div>
          )}
        </div>
        <label className="block">
          显示名称（可选）
          <input
            className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 transition-all focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="便于在列表中识别"
          />
        </label>
        <label className="block">
          模型名（如 openai/gpt-4o-mini）
          <input
            className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 transition-all focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30"
            value={model}
            onChange={(e) => setModel(e.target.value)}
          />
        </label>
        <label className="block">
          API Base（可选，兼容 OpenAI 网关）
          <input
            className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 transition-all focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30"
            value={apiBase}
            onChange={(e) => setApiBase(e.target.value)}
          />
        </label>
        <label className="block">
          API Key
          <input
            type="password"
            className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 transition-all focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30"
            value={apiKey}
            placeholder={
              selectedKey !== 'new' && profiles.find((p) => p.id === selectedKey)?.api_key_set
                ? '已配置，留空则不修改'
                : ''
            }
            onChange={(e) => setApiKey(e.target.value)}
          />
        </label>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className="rounded-lg bg-accent px-4 py-2 text-sm text-white transition-colors hover:bg-accent-hover active:scale-[0.98] disabled:opacity-50"
            onClick={() => void onSave()}
            disabled={validation.errors.length > 0}
          >
            {selectedKey === 'new' ? '保存为新模型' : '保存修改'}
          </button>
          <button
            type="button"
            className="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
            onClick={onNewBlank}
          >
            新建空白
          </button>
        </div>
      </div>
    </>
  );
}
