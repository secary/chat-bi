import { describe, expect, it } from 'vitest';
import { validateLlmConfig } from './llmConfigValidation';

describe('validateLlmConfig', () => {
  it('returns error when openai-compatible base uses non-openai model prefix', () => {
    const out = validateLlmConfig('gpt-4o-mini', 'https://api.minimaxi.com/v1');
    expect(out.errors).toHaveLength(1);
  });

  it('passes when model has openai prefix', () => {
    const out = validateLlmConfig('openai/MiniMax-M2.5', 'https://api.minimaxi.com/v1');
    expect(out.errors).toHaveLength(0);
  });
});
