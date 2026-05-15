export interface TableBlock {
  type: 'table';
  header: string[];
  rows: string[][];
}

export interface HeadingBlock {
  type: 'heading';
  level: number;
  content: string;
}

export interface HrBlock {
  type: 'hr';
}

export interface MathBlock {
  type: 'math';
  latex: string;
  display: boolean;
}

export interface LineBlock {
  type: 'line';
  content: string;
}

export type MarkdownBlock = LineBlock | TableBlock | HeadingBlock | HrBlock | MathBlock;

const TABLE_SEPARATOR_RE = /^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?$/;
const HR_RE = /^(-{3,}|\*{3,}|_{3,})$/;
const HEADING_RE = /^(#{1,6})\s+(.+)$/;

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

function parseMathBlock(lines: string[], start: number): { block: MathBlock; next: number } | null {
  const first = lines[start].trim();
  if (!first.startsWith('$$')) return null;

  if (first.endsWith('$$') && first.length > 4) {
    return {
      block: { type: 'math', latex: first.slice(2, -2).trim(), display: true },
      next: start + 1,
    };
  }

  let latex = first.slice(2).trim();
  let i = start + 1;
  while (i < lines.length) {
    const row = lines[i];
    const trimmed = row.trim();
    if (trimmed.endsWith('$$')) {
      const tail = trimmed.slice(0, -2).trim();
      if (tail) {
        latex = latex ? `${latex}\n${tail}` : tail;
      }
      return { block: { type: 'math', latex: latex.trim(), display: true }, next: i + 1 };
    }
    latex = latex ? `${latex}\n${row}` : row;
    i += 1;
  }
  return { block: { type: 'math', latex: latex.trim(), display: true }, next: i };
}

export function parseMarkdownBlocks(content: string): MarkdownBlock[] {
  const lines = content.split('\n');
  const blocks: MarkdownBlock[] = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();
    const next = (lines[i + 1] || '').trim();

    const math = parseMathBlock(lines, i);
    if (math) {
      blocks.push(math.block);
      i = math.next;
      continue;
    }

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

    if (!trimmed) {
      blocks.push({ type: 'line', content: '' });
      i += 1;
      continue;
    }

    if (HR_RE.test(trimmed)) {
      blocks.push({ type: 'hr' });
      i += 1;
      continue;
    }

    const heading = trimmed.match(HEADING_RE);
    if (heading) {
      blocks.push({
        type: 'heading',
        level: heading[1].length,
        content: heading[2].trim(),
      });
      i += 1;
      continue;
    }

    blocks.push({ type: 'line', content: line });
    i += 1;
  }
  return blocks;
}
