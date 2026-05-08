import { describe, expect, it } from 'vitest';
import { clampMaxAgentsRound, isValidAgentId } from './multiAgentsRegistryUi';

describe('multiAgentsRegistryUi', () => {
  it('clampMaxAgentsRound bounds to 1–8', () => {
    expect(clampMaxAgentsRound(0)).toBe(1);
    expect(clampMaxAgentsRound(1)).toBe(1);
    expect(clampMaxAgentsRound(8)).toBe(8);
    expect(clampMaxAgentsRound(99)).toBe(8);
    expect(clampMaxAgentsRound(NaN)).toBe(2);
  });

  it('isValidAgentId rejects leading underscore', () => {
    expect(isValidAgentId('_bad')).toBe(false);
    expect(isValidAgentId('risk')).toBe(true);
    expect(isValidAgentId('')).toBe(false);
  });
});
