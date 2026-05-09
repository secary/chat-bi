export interface LlmProviderPreset {
  id: string;
  label: string;
  model: string;
  apiBase: string;
}

export const LLM_PROVIDER_PRESETS: LlmProviderPreset[] = [
  {
    id: 'openai',
    label: 'OpenAI',
    model: 'openai/gpt-4o-mini',
    apiBase: 'https://api.openai.com/v1',
  },
  {
    id: 'anthropic',
    label: 'Anthropic',
    model: 'anthropic/claude-3-5-sonnet-latest',
    apiBase: 'https://api.anthropic.com',
  },
  {
    id: 'ark',
    label: 'ARK',
    model: 'openai/doubao-1-5-pro-32k-250115',
    apiBase: 'https://ark.cn-beijing.volces.com/api/v3',
  },
  {
    id: 'minimax',
    label: 'MiniMax',
    model: 'openai/MiniMax-M2.5',
    apiBase: 'https://api.minimaxi.com/v1',
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
