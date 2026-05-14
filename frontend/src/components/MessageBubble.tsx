import type { ChatMessage } from '../types/message';
import { ThinkingBubble } from './ThinkingBubble';
import { ChartRenderer } from './ChartRenderer';
import { KPICards } from './KPICards';
import { tokenizeInlineMarkdown } from '../lib/inlineMarkdown';
import { parseMarkdownBlocks } from '../lib/markdownBlocks';

interface MessageBubbleProps {
  message: ChatMessage;
}

function renderInline(content: string) {
  return tokenizeInlineMarkdown(content).map((token, idx) =>
    token.type === 'bold' ? (
      <strong key={idx} className="font-semibold text-gray-900">
        {token.value}
      </strong>
    ) : (
      <span key={idx}>{token.value}</span>
    ),
  );
}

function FormattedContent({ content }: { content: string }) {
  const blocks = parseMarkdownBlocks(content);
  return (
    <div className="space-y-1">
      {blocks.map((block, index) => {
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

        const trimmed = block.content.trim();
        if (!trimmed) {
          return <div key={index} className="h-2" />;
        }
        if (trimmed.startsWith('## ')) {
          return (
            <h2 key={index} className="pt-1 text-base font-semibold tracking-tight text-gray-950">
              {renderInline(trimmed.slice(3))}
            </h2>
          );
        }
        if (trimmed.startsWith('### ')) {
          return (
            <h3 key={index} className="pt-3 text-sm font-semibold text-gray-900">
              {renderInline(trimmed.slice(4))}
            </h3>
          );
        }
        if (/^\d+\.\s/.test(trimmed)) {
          return (
            <p key={index} className="pt-2 text-sm font-semibold text-gray-900">
              {renderInline(trimmed)}
            </p>
          );
        }
        if (/^[-•]\s+/.test(trimmed)) {
          return (
            <div key={index} className="flex gap-2 text-sm text-gray-700">
              <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-gray-400/60" />
              <span>{renderInline(trimmed.slice(2))}</span>
            </div>
          );
        }
        return (
          <p key={index} className="text-sm text-gray-700">
            {renderInline(trimmed)}
          </p>
        );
      })}
    </div>
  );
}

function AnalysisProposalCard({
  proposal,
}: {
  proposal: NonNullable<ChatMessage['analysisProposal']>;
}) {
  return (
    <div className="mt-3 rounded-xl border border-emerald-200 bg-emerald-50/60 px-4 py-3">
      <FormattedContent content={proposal.markdown} />
      <div className="mt-3 grid gap-2 md:grid-cols-2">
        {proposal.proposed_metrics.map((metric) => (
          <div key={metric.id} className="rounded-lg border border-emerald-200 bg-white px-3 py-2">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="text-sm font-semibold text-gray-950">{metric.name}</div>
                <div className="mt-1 text-xs text-gray-600">{metric.description}</div>
              </div>
              <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">
                {Math.round(metric.confidence * 100)}%
              </span>
            </div>
            <div className="mt-2 text-xs text-gray-600">{metric.formula_md}</div>
            <div className="mt-2 text-xs text-gray-500">
              ID: <span className="font-mono">{metric.id}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function DashboardMiddlewareCard({
  dashboard,
}: {
  dashboard: NonNullable<ChatMessage['dashboardReady']>;
}) {
  return (
    <div className="mt-3 rounded-xl border border-sky-200 bg-sky-50/60 px-4 py-3">
      <FormattedContent content={dashboard.markdown} />
      <div className="mt-3 grid gap-2 md:grid-cols-2">
        {dashboard.widgets.map((widget) => (
          <div key={widget.id} className="rounded-lg border border-sky-200 bg-white px-3 py-2">
            <div className="text-sm font-semibold text-gray-950">{widget.title}</div>
            <div className="mt-1 text-xs text-gray-500">
              {widget.type} · 图表 #{widget.chart_index + 1}
            </div>
          </div>
        ))}
      </div>
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
        {message.analysisProposal && <AnalysisProposalCard proposal={message.analysisProposal} />}
        {message.dashboardReady && <DashboardMiddlewareCard dashboard={message.dashboardReady} />}

        {message.error && (
          <div className="mt-2 rounded-xl border border-red-200 bg-red-50/80 px-4 py-3 text-sm text-red-700">
            {message.error}
          </div>
        )}
      </div>
    </div>
  );
}
