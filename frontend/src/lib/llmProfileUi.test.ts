import { describe, expect, it } from 'vitest';
import { healthStatusLabel, profileListTitle } from './llmProfileUi';

describe('llmProfileUi', () => {
  it('prefers display name over model', () => {
    expect(profileListTitle('  Prod  ', 'openai/x')).toBe('Prod');
  });

  it('falls back to model', () => {
    expect(profileListTitle(null, 'openai/x')).toBe('openai/x');
  });

  it('maps health status labels', () => {
    expect(healthStatusLabel('ok')).toBe('可用');
    expect(healthStatusLabel('error')).toBe('不可用');
    expect(healthStatusLabel('unknown')).toBe('未检测');
  });
});
