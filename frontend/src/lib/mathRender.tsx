import { useMemo } from 'react';
import katex from 'katex';

export function renderKatexHtml(latex: string, displayMode: boolean): string | null {
  try {
    return katex.renderToString(latex.trim(), {
      displayMode,
      throwOnError: false,
      strict: 'ignore',
    });
  } catch {
    return null;
  }
}

export function KaTeXMath({ latex, display = false }: { latex: string; display?: boolean }) {
  const html = useMemo(() => renderKatexHtml(latex, display), [latex, display]);
  if (!html) {
    return (
      <code className="rounded bg-gray-100 px-1.5 py-0.5 font-mono text-xs text-gray-700">{latex}</code>
    );
  }
  if (display) {
    return (
      <div
        className="my-3 overflow-x-auto rounded-lg border border-gray-100 bg-gray-50/90 px-4 py-3 text-center [&_.katex]:text-base"
        dangerouslySetInnerHTML={{ __html: html }}
      />
    );
  }
  return (
    <span
      className="inline [&_.katex]:text-[0.95em]"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
