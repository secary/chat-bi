import { describe, expect, it } from 'vitest';
import { tokenizeInlineMarkdown } from './inlineMarkdown';

describe('tokenizeInlineMarkdown', () => {
  it('parses bold markers into bold tokens', () => {
    expect(tokenizeInlineMarkdown('**时间范围**：2026年5月6日~10日')).toEqual([
      { type: 'bold', value: '时间范围' },
      { type: 'text', value: '：2026年5月6日~10日' },
    ]);
  });

  it('keeps plain text unchanged', () => {
    expect(tokenizeInlineMarkdown('普通文本')).toEqual([{ type: 'text', value: '普通文本' }]);
  });

  it('supports multiple bold segments in one line', () => {
    expect(tokenizeInlineMarkdown('**区域**：华东，**渠道**：直营')).toEqual([
      { type: 'bold', value: '区域' },
      { type: 'text', value: '：华东，' },
      { type: 'bold', value: '渠道' },
      { type: 'text', value: '：直营' },
    ]);
  });

  it('parses inline and display math', () => {
    expect(tokenizeInlineMarkdown('率 $a/b$ 与 $$x=1$$')).toEqual([
      { type: 'text', value: '率 ' },
      { type: 'math', value: 'a/b', display: false },
      { type: 'text', value: ' 与 ' },
      { type: 'math', value: 'x=1', display: true },
    ]);
  });
});
