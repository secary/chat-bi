declare module 'katex' {
  interface RenderOptions {
    displayMode?: boolean;
    throwOnError?: boolean;
    strict?: 'ignore' | boolean | string;
  }

  interface KatexApi {
    renderToString(input: string, options?: RenderOptions): string;
  }

  const katex: KatexApi;
  export default katex;
}
