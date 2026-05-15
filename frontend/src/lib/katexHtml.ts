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
