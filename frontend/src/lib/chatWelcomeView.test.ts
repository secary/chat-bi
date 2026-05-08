import { describe, expect, it } from 'vitest';
import { shouldShowChatWelcomeView } from './chatWelcomeView';

describe('shouldShowChatWelcomeView', () => {
  it('is false while booting', () => {
    expect(shouldShowChatWelcomeView(true, 0)).toBe(false);
    expect(shouldShowChatWelcomeView(true, 3)).toBe(false);
  });

  it('is true when loaded and no messages', () => {
    expect(shouldShowChatWelcomeView(false, 0)).toBe(true);
  });

  it('is false when any message exists', () => {
    expect(shouldShowChatWelcomeView(false, 1)).toBe(false);
    expect(shouldShowChatWelcomeView(false, 10)).toBe(false);
  });
});
