/** Thin wrapper so we avoid raw console.log (project convention). */

export const logger = {
  debug: (...args: unknown[]) => {
    if (import.meta.env.DEV) {
      console.debug('[chatbi]', ...args);
    }
  },
  error: (...args: unknown[]) => {
    console.error('[chatbi]', ...args);
  },
};
