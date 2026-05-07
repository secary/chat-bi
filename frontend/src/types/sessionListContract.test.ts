import { describe, expect, it } from 'vitest';
import type { SessionListApi } from './admin';

describe('SessionListApi', () => {
  it('includes sessions and suggested_prompts', () => {
    const data: SessionListApi = {
      sessions: [],
      suggested_prompts: ['1-4月销售额'],
    };
    expect(data.suggested_prompts).toHaveLength(1);
  });
});
