import { describe, expect, it } from 'vitest';
import { LLM_PROVIDER_PRESETS, detectPreset } from './llmProviderPresets';

describe('llmProviderPresets', () => {
  it('contains required provider presets', () => {
    const ids = LLM_PROVIDER_PRESETS.map((p) => p.id);
    expect(ids).toEqual(['openai', 'anthropic', 'ark', 'minimax']);
  });

  it('detects matching preset by model and api base', () => {
    expect(detectPreset('openai/MiniMax-M2.5', 'https://api.minimaxi.com/v1')).toBe('minimax');
  });

  it('returns empty when no preset matches', () => {
    expect(detectPreset('openai/gpt-4.1', 'https://example.com/v1')).toBe('');
  });
});
