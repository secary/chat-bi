import { ChatInput } from './ChatInput';
import type { UploadedFile } from '../types/message';

interface ChatComposerDockProps {
  onSend: (text: string, traceId?: string, uploads?: UploadedFile[]) => void;
  onAbort?: () => void;
  inputBusy: boolean;
  booting: boolean;
  sessionId: number | null;
  variant?: 'dock' | 'welcome';
}

export function ChatComposerDock({
  onSend,
  onAbort,
  inputBusy,
  booting,
  sessionId,
  variant = 'dock',
}: ChatComposerDockProps) {
  return (
    <ChatInput
      onSend={onSend}
      onAbort={onAbort}
      loading={inputBusy}
      disabled={booting || sessionId == null}
      variant={variant}
    />
  );
}
