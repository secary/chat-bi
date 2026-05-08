import { describe, expect, it } from 'vitest';
import { isWaitingForAssistantMessage } from './chatPending';

describe('isWaitingForAssistantMessage', () => {
  it('false when no session', () => {
    expect(isWaitingForAssistantMessage(null, [{ role: 'user' }])).toBe(false);
  });

  it('false when empty messages', () => {
    expect(isWaitingForAssistantMessage(1, [])).toBe(false);
  });

  it('true when last message is user', () => {
    expect(
      isWaitingForAssistantMessage(1, [{ role: 'assistant' }, { role: 'user' }]),
    ).toBe(true);
  });

  it('false when last message is assistant', () => {
    expect(
      isWaitingForAssistantMessage(1, [{ role: 'user' }, { role: 'assistant' }]),
    ).toBe(false);
  });
});
