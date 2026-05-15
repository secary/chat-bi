export interface InlineToken {
  type: 'text' | 'bold' | 'math';
  value: string;
  display?: boolean;
}

export function tokenizeInlineMarkdown(text: string): InlineToken[] {
  if (!text) return [];
  const tokens: InlineToken[] = [];
  const pattern = /\*\*([^*]+)\*\*|\$\$([^$]+)\$\$|\$([^$\n]+)\$/g;
  let last = 0;
  let match: RegExpExecArray | null;

  while ((match = pattern.exec(text)) !== null) {
    const start = match.index;
    if (start > last) {
      tokens.push({ type: 'text', value: text.slice(last, start) });
    }
    if (match[1] !== undefined) {
      tokens.push({ type: 'bold', value: match[1] });
    } else if (match[2] !== undefined) {
      tokens.push({ type: 'math', value: match[2], display: true });
    } else if (match[3] !== undefined) {
      tokens.push({ type: 'math', value: match[3], display: false });
    }
    last = start + match[0].length;
  }

  if (last < text.length) {
    tokens.push({ type: 'text', value: text.slice(last) });
  }
  return tokens.length ? tokens : [{ type: 'text', value: text }];
}
