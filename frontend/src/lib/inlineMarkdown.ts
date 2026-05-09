export interface InlineToken {
  type: 'text' | 'bold';
  value: string;
}

export function tokenizeInlineMarkdown(text: string): InlineToken[] {
  if (!text) return [];
  const tokens: InlineToken[] = [];
  const pattern = /\*\*([^*]+)\*\*/g;
  let last = 0;
  let match: RegExpExecArray | null;

  while ((match = pattern.exec(text)) !== null) {
    const [full, boldText] = match;
    const start = match.index;
    if (start > last) {
      tokens.push({ type: 'text', value: text.slice(last, start) });
    }
    tokens.push({ type: 'bold', value: boldText });
    last = start + full.length;
  }

  if (last < text.length) {
    tokens.push({ type: 'text', value: text.slice(last) });
  }
  return tokens.length ? tokens : [{ type: 'text', value: text }];
}
