import type { ChatMessage } from '../types/message';
import { ThinkingBubble } from './ThinkingBubble';
import { ChartRenderer } from './ChartRenderer';
import { KPICards } from './KPICards';

interface MessageBubbleProps {
  message: ChatMessage;
}

function FormattedContent({ content }: { content: string }) {
  return (
    <div className="space-y-1">
      {content.split('\n').map((line, index) => {
        const trimmed = line.trim();
        if (!trimmed) {
          return <div key={index} className="h-2" />;
        }
        if (trimmed.startsWith('## ')) {
          return (
            <h2 key={index} className="pt-1 text-base font-semibold tracking-tight text-gray-950">
              {trimmed.slice(3)}
            </h2>
          );
        }
        if (trimmed.startsWith('### ')) {
          return (
            <h3 key={index} className="pt-3 text-sm font-semibold text-gray-900">
              {trimmed.slice(4)}
            </h3>
          );
        }
        if (/^\d+\.\s/.test(trimmed)) {
          return (
            <p key={index} className="pt-2 text-sm font-semibold text-gray-900">
              {trimmed}
            </p>
          );
        }
        if (trimmed.startsWith('- ')) {
          return (
            <div key={index} className="flex gap-2 text-sm text-gray-700">
              <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-gray-400/60" />
              <span>{trimmed.slice(2)}</span>
            </div>
          );
        }
        return (
          <p key={index} className="text-sm text-gray-700">
            {trimmed}
          </p>
        );
      })}
    </div>
  );
}

export function MessageBubble({ message }: MessageBubbleProps) {
  if (message.role === 'user') {
    return (
      <div className="mb-4 flex justify-end animate-fade-in">
        <div className="max-w-[80%] rounded-2xl rounded-br-sm bg-accent px-4 py-3 text-sm text-white leading-relaxed">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="mb-4 animate-fade-in">
      <div className="max-w-[90%]">
        <div className="mb-1 flex items-center gap-2">
          <span className="flex h-7 w-7 items-center justify-center rounded-full bg-gray-100 text-xs font-semibold text-gray-500">
            AI
          </span>
          <span className="text-xs font-medium text-gray-500">ChatBI</span>
        </div>

        <ThinkingBubble steps={message.thinking || []} />

        {message.content && (
          <div className="prose prose-sm max-w-none rounded-2xl rounded-tl-sm bg-surface px-5 py-3.5 text-sm leading-relaxed text-gray-800 shadow-card">
            <FormattedContent content={message.content} />
          </div>
        )}

        {message.chart && <ChartRenderer option={message.chart} />}
        {message.kpiCards && <KPICards cards={message.kpiCards} />}

        {message.error && (
          <div className="mt-2 rounded-xl border border-red-200 bg-red-50/80 px-4 py-3 text-sm text-red-700">
            {message.error}
          </div>
        )}
      </div>
    </div>
  );
}
