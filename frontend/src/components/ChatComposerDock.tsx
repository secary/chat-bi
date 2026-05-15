import { ChatInput } from './ChatInput';

interface ChatComposerDockProps {
  suggestedPrompts: string[];
  onSend: (text: string, traceId?: string) => void;
  onAbort?: () => void;
  inputBusy: boolean;
  booting: boolean;
  sessionId: number | null;
}

export function ChatComposerDock({
  suggestedPrompts,
  onSend,
  onAbort,
  inputBusy,
  booting,
  sessionId,
}: ChatComposerDockProps) {
  return (
    <>
      {suggestedPrompts.length > 0 ? (
        <div className="mb-3 flex flex-wrap gap-2">
          <span className="w-full text-xs text-gray-400">记忆提示 · 可快捷继续：</span>
          {suggestedPrompts.map((p, idx) => (
            <button
              key={`${idx}-${p.slice(0, 40)}`}
              type="button"
              onClick={() => void onSend(p)}
              disabled={inputBusy || booting || sessionId == null}
              className="max-w-full truncate rounded-full border border-amber-200 bg-amber-50 px-3.5 py-1.5 text-left text-xs text-amber-900 transition-colors hover:bg-amber-100 disabled:opacity-50"
              title={p}
            >
              {p}
            </button>
          ))}
        </div>
      ) : null}
      <ChatInput onSend={onSend} onAbort={onAbort} loading={inputBusy} disabled={booting || sessionId == null} />
    </>
  );
}
