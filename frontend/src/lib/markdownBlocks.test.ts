import { describe, expect, it } from 'vitest';
import { parseMarkdownBlocks } from './markdownBlocks';

describe('parseMarkdownBlocks', () => {
  it('parses markdown table into structured block', () => {
    const content = [
      '详细分析如下：',
      '',
      '| 区域 | 销售额 (元) | 毛利润 (元) |',
      '| :--- | :--- | :--- |',
      '| 华东 | 288,700.00 | 100,600.00 |',
      '| 华南 | 89,500.50 | 31,200.00 |',
    ].join('\n');
    const blocks = parseMarkdownBlocks(content);
    expect(blocks[2]).toEqual({
      type: 'table',
      header: ['区域', '销售额 (元)', '毛利润 (元)'],
      rows: [
        ['华东', '288,700.00', '100,600.00'],
        ['华南', '89,500.50', '31,200.00'],
      ],
    });
  });

  it('keeps normal lines as line blocks', () => {
    const blocks = parseMarkdownBlocks('普通文本\n- 列表');
    expect(blocks).toEqual([
      { type: 'line', content: '普通文本' },
      { type: 'line', content: '- 列表' },
    ]);
  });
});
