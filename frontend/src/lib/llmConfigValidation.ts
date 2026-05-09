export interface LlmConfigValidation {
  errors: string[];
  warnings: string[];
}

function normalizeBase(apiBase: string): string {
  return apiBase.trim().toLowerCase().replace(/\/+$/, '');
}

function isOpenAiCompatibleBase(apiBase: string): boolean {
  const base = normalizeBase(apiBase);
  return (
    base.includes('/v1') &&
    (base.includes('openai.com') ||
      base.includes('minimaxi.com') ||
      base.includes('dashscope.aliyuncs.com') ||
      base.includes('siliconflow.cn') ||
      base.includes('volces.com'))
  );
}

export function validateLlmConfig(model: string, apiBase: string): LlmConfigValidation {
  const errors: string[] = [];
  const warnings: string[] = [];
  const m = model.trim();
  const base = apiBase.trim();

  if (base && isOpenAiCompatibleBase(base) && m && !m.startsWith('openai/')) {
    errors.push(
      '当前 API Base 是 OpenAI 兼容网关，模型名需使用 openai/<具体模型名>（例如 openai/gpt-4o-mini）。',
    );
  }
  if (m && !m.includes('/')) {
    warnings.push('建议使用 provider/model 格式，避免 LiteLLM 无法正确识别 provider。');
  }
  return { errors, warnings };
}
