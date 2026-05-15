import type { JSX, ReactNode } from 'react';
import { tokenizeInlineMarkdown } from './inlineMarkdown';
import { parseMarkdownBlocks, type MarkdownBlock } from './markdownBlocks';
import { KaTeXMath } from './mathRender';

const HEADING_CLASS: Record<number, string> = {
  1: 'pt-2 text-lg font-semibold tracking-tight text-gray-950',
  2: 'pt-1 text-base font-semibold tracking-tight text-gray-950',
  3: 'pt-3 text-sm font-semibold text-gray-900',
  4: 'pt-2 text-sm font-semibold text-gray-900',
  5: 'pt-2 text-xs font-semibold uppercase tracking-wide text-gray-800',
  6: 'pt-2 text-xs font-semibold text-gray-700',
};

function renderInline(content: string): ReactNode[] {
  return tokenizeInlineMarkdown(content).map((token, idx) => {
    if (token.type === 'bold') {
      return (
        <strong key={idx} className="font-semibold text-gray-900">
          {token.value}
        </strong>
      );
    }
    if (token.type === 'math') {
      return <KaTeXMath key={idx} latex={token.value} display={token.display} />;
    }
    return <span key={idx}>{token.value}</span>;
  });
}

function renderLineBlock(content: string, key: number) {
  const trimmed = content.trim();
  if (!trimmed) {
    return <div key={key} className="h-2" />;
  }

  const bullet = trimmed.match(/^(\s*)([-•*])\s+(.+)$/);
  if (bullet) {
    const indent = bullet[1].length;
    const level = Math.min(3, Math.floor(indent / 2));
    return (
      <div
        key={key}
        className="flex gap-2 text-sm text-gray-700"
        style={{ paddingLeft: `${level * 0.75}rem` }}
      >
        <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-gray-400/60" />
        <span>{renderInline(bullet[3])}</span>
      </div>
    );
  }

  if (/^\d+\.\s/.test(trimmed)) {
    return (
      <p key={key} className="pt-2 text-sm font-semibold text-gray-900">
        {renderInline(trimmed)}
      </p>
    );
  }

  return (
    <p key={key} className="text-sm leading-relaxed text-gray-700">
      {renderInline(trimmed)}
    </p>
  );
}

function renderBlock(block: MarkdownBlock, index: number) {
  if (block.type === 'table') {
    return (
      <div key={index} className="my-2 overflow-x-auto rounded-lg border border-gray-200">
        <table className="min-w-full border-collapse text-sm">
          <thead className="bg-gray-50">
            <tr>
              {block.header.map((cell, hIdx) => (
                <th
                  key={hIdx}
                  className="border-b border-gray-200 px-3 py-2 text-left font-semibold text-gray-800"
                >
                  {renderInline(cell)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {block.rows.map((row, rIdx) => (
              <tr key={rIdx} className="border-b border-gray-100 last:border-b-0">
                {row.map((cell, cIdx) => (
                  <td key={cIdx} className="px-3 py-2 align-top text-gray-700">
                    {renderInline(cell)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  if (block.type === 'heading') {
    const level = Math.min(6, Math.max(1, block.level));
    const Tag = `h${level}` as keyof JSX.IntrinsicElements;
    return (
      <Tag key={index} className={HEADING_CLASS[level]}>
        {renderInline(block.content)}
      </Tag>
    );
  }

  if (block.type === 'hr') {
    return <hr key={index} className="my-3 border-0 border-t border-gray-200" />;
  }

  if (block.type === 'math') {
    return <KaTeXMath key={index} latex={block.latex} display={block.display} />;
  }

  return renderLineBlock(block.content, index);
}

export function FormattedMarkdown({ content }: { content: string }) {
  const blocks = parseMarkdownBlocks(content);
  return <div className="space-y-1">{blocks.map(renderBlock)}</div>;
}
