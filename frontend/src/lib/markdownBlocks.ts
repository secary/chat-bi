export interface TableBlock {
  type: 'table';
  header: string[];
  rows: string[][];
}

export interface LineBlock {
  type: 'line';
  content: string;
}

export type MarkdownBlock = LineBlock | TableBlock;

const TABLE_SEPARATOR_RE = /^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?$/;

function isPipeRow(trimmed: string): boolean {
  return trimmed.startsWith('|') && trimmed.endsWith('|');
}

function parsePipeRow(line: string): string[] {
  return line
    .trim()
    .replace(/^\|/, '')
    .replace(/\|$/, '')
    .split('|')
    .map((cell) => cell.trim());
}

export function parseMarkdownBlocks(content: string): MarkdownBlock[] {
  const lines = content.split('\n');
  const blocks: MarkdownBlock[] = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();
    const next = (lines[i + 1] || '').trim();
    if (isPipeRow(trimmed) && TABLE_SEPARATOR_RE.test(next)) {
      const header = parsePipeRow(trimmed);
      i += 2;
      const rows: string[][] = [];
      while (i < lines.length) {
        const rowLine = lines[i].trim();
        if (!isPipeRow(rowLine)) break;
        rows.push(parsePipeRow(rowLine));
        i += 1;
      }
      blocks.push({ type: 'table', header, rows });
      continue;
    }
    blocks.push({ type: 'line', content: line });
    i += 1;
  }
  return blocks;
}
