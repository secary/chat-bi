export interface LlmProviderPreset {
  id: string;
  label: string;
  model: string;
  apiBase: string;
  modelRule: string;
  note: string;
}

export const LLM_PROVIDER_PRESETS: LlmProviderPreset[] = [
  {
    id: 'openai',
    label: 'OpenAI',
    model: 'openai/gpt-4o-mini',
    apiBase: 'https://api.openai.com/v1',
    modelRule: '模型建议：openai/<model>',
    note: '官方 OpenAI 兼容网关，推荐直接使用 openai/ 前缀模型名。',
  },
  {
    id: 'anthropic',
    label: 'Anthropic',
    model: 'anthropic/claude-3-5-sonnet-latest',
    apiBase: 'https://api.anthropic.com',
    modelRule: '模型建议：anthropic/<model>',
    note: '原生 Anthropic 路由，推荐使用 anthropic/ 前缀。',
  },
  {
    id: 'ark',
    label: 'ARK',
    model: 'openai/doubao-1-5-pro-32k-250115',
    apiBase: 'https://ark.cn-beijing.volces.com/api/v3',
    modelRule: '模型建议：openai/<ARK 模型名>',
    note: 'ARK 是 OpenAI 兼容网关，模型名需走 openai/ 前缀。',
  },
  {
    id: 'minimax',
    label: 'MiniMax',
    model: 'openai/MiniMax-M2.5',
    apiBase: 'https://api.minimaxi.com/v1',
    modelRule: '模型建议：openai/<MiniMax 模型名>',
    note: 'MiniMax OpenAPI 网关需使用 openai/ 前缀模型名。',
  },
  {
    id: 'deepseek',
    label: 'DeepSeek',
    model: 'openai/deepseek-v4-flash',
    apiBase: 'https://api.deepseek.com',
    modelRule: '模型建议：openai/<DeepSeek 模型名>',
    note: 'DeepSeek OpenAI 兼容网关建议使用 openai/ 前缀（如 openai/deepseek-v4-flash）。',
  },
];

export function detectPreset(model: string, apiBase: string): string {
  const m = model.trim().toLowerCase();
  const b = apiBase.trim().toLowerCase().replace(/\/+$/, '');
  const matched = LLM_PROVIDER_PRESETS.find(
    (preset) =>
      preset.model.toLowerCase() === m &&
      preset.apiBase.toLowerCase().replace(/\/+$/, '') === b,
  );
  return matched?.id || '';
}
