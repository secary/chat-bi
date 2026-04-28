import type { ChatMessage } from '../types/message';
import { ThinkingBubble } from './ThinkingBubble';
import { ChartRenderer } from './ChartRenderer';
import { KPICards } from './KPICards';

interface MessageBubbleProps {
  message: ChatMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  if (message.role === 'user') {
    return (
      <div className="mb-4 flex justify-end">
        <div className="max-w-[80%] rounded-2xl rounded-br-md bg-blue-600 px-4 py-2.5 text-sm text-white">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="mb-4">
      <div className="max-w-[90%]">
        <div className="mb-1 flex items-center gap-2">
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-gray-200 text-xs font-semibold text-gray-600">
            AI
          </span>
          <span className="text-xs font-medium text-gray-500">ChatBI</span>
        </div>

        <ThinkingBubble steps={message.thinking || []} />

        {message.content && (
          <div className="prose prose-sm max-w-none rounded-2xl rounded-tl-md bg-white px-4 py-2.5 text-sm leading-relaxed text-gray-800 shadow-sm">
            <div className="whitespace-pre-wrap">{message.content}</div>
          </div>
        )}

        {message.chart && <ChartRenderer option={message.chart} />}
        {message.kpiCards && <KPICards cards={message.kpiCards} />}

        {message.error && (
          <div className="mt-2 rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
            {message.error}
          </div>
        )}
      </div>
    </div>
  );
}
