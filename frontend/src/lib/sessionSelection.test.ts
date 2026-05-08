import { describe, expect, it } from 'vitest';
import { resolveInitialSessionId } from './sessionSelection';

describe('resolveInitialSessionId', () => {
  it('returns stored id when present in list', () => {
    expect(
      resolveInitialSessionId([{ id: 1 }, { id: 2 }, { id: 3 }], 2),
    ).toBe(2);
  });

  it('falls back to first session when stored is missing', () => {
    expect(resolveInitialSessionId([{ id: 10 }, { id: 20 }], 99)).toBe(10);
  });

  it('falls back when stored is null', () => {
    expect(resolveInitialSessionId([{ id: 7 }], null)).toBe(7);
  });
});
