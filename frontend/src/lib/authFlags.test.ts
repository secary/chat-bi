import { describe, expect, it } from 'vitest';
import { parseAuthEnabled } from './authFlags';

describe('parseAuthEnabled', () => {
  it('treats unset as enabled', () => {
    expect(parseAuthEnabled(undefined)).toBe(true);
    expect(parseAuthEnabled('')).toBe(true);
  });

  it('disables for common false literals', () => {
    expect(parseAuthEnabled('0')).toBe(false);
    expect(parseAuthEnabled('false')).toBe(false);
    expect(parseAuthEnabled('OFF')).toBe(false);
  });

  it('enables for other values', () => {
    expect(parseAuthEnabled('1')).toBe(true);
    expect(parseAuthEnabled('yes')).toBe(true);
  });
});
