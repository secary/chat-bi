/** Shown when the last persisted message is user — assistant row not in DB yet (e.g. user navigated away during generation). */

export function AssistantPendingNotice() {
  return (
    <div
      className="mb-4 flex items-start gap-3 rounded-2xl border border-accent/20 bg-accent-light/80 px-5 py-3.5 text-sm text-accent shadow-card"
      role="status"
      aria-live="polite"
      aria-busy="true"
    >
      <span
        className="mt-0.5 inline-flex h-5 w-5 shrink-0 animate-spin rounded-full border-2 border-accent border-t-transparent"
        aria-hidden
      />
      <div>
        <p className="font-medium text-accent">助手正在生成回复</p>
        <p className="mt-0.5 text-xs text-gray-500">
          您离开页面期间回复仍在后台继续处理，同步后会自动显示在下面。
        </p>
      </div>
    </div>
  );
}
