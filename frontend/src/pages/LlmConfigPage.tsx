import { useEffect, useState } from 'react';
import { getLlmSettings, putLlmSettings } from '../api/client';
import type { LlmSettingsView } from '../types/admin';
import { logger } from '../lib/logger';

export function LlmConfigPage() {
  const [view, setView] = useState<LlmSettingsView | null>(null);
  const [model, setModel] = useState('');
  const [apiBase, setApiBase] = useState('');
  const [apiKey, setApiKey] = useState('');

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
    try {
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
    } catch (e) {
      logger.error('save llm', e);
    }
  };

  return (
    <div className="h-full overflow-auto p-6">
      <h2 className="mb-4 text-lg font-semibold text-gray-900">LLM 配置</h2>
      <p className="mb-4 max-w-xl text-sm text-gray-600">
        此处保存的配置会覆盖进程环境变量中的 `LLM_MODEL` / `API_BASE` / `OPENAI_API_KEY`（非空字段）。
        {view?.updated_at ? ` 最近更新：${String(view.updated_at)}` : ''}
      </p>
      <div className="max-w-xl space-y-3 rounded-lg border border-gray-200 bg-white p-4 text-sm">
        <label className="block">
          模型名（如 openai/gpt-4o-mini）
          <input
            className="mt-1 w-full rounded border border-gray-300 px-2 py-1"
            value={model}
            onChange={(e) => setModel(e.target.value)}
          />
        </label>
        <label className="block">
          API Base（可选，兼容 OpenAI 网关）
          <input
            className="mt-1 w-full rounded border border-gray-300 px-2 py-1"
            value={apiBase}
            onChange={(e) => setApiBase(e.target.value)}
          />
        </label>
        <label className="block">
          API Key
          <input
            type="password"
            className="mt-1 w-full rounded border border-gray-300 px-2 py-1"
            value={apiKey}
            placeholder={view?.api_key_set ? '已配置，留空则不修改' : ''}
            onChange={(e) => setApiKey(e.target.value)}
          />
        </label>
        <button
          type="button"
          className="rounded bg-blue-600 px-4 py-2 text-white"
          onClick={() => void save()}
        >
          保存
        </button>
      </div>
    </div>
  );
}
