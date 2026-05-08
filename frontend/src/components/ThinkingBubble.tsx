import { useState } from 'react';

interface ThinkingBubbleProps {
  steps: string[];
}

export function ThinkingBubble({ steps }: ThinkingBubbleProps) {
  const [collapsed, setCollapsed] = useState(false);

  if (steps.length === 0) return null;

  return (
    <div className="mb-3 rounded-xl border border-gray-200/60 bg-gray-50/70 px-4 py-2.5">
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="flex items-center gap-1 text-sm text-gray-500 transition-colors hover:text-gray-700"
      >
        <span className="text-xs">{collapsed ? '▶' : '▼'}</span>
        <span>思考步骤 ({steps.length})</span>
      </button>
      {!collapsed && (
        <ul className="mt-2 space-y-1.5">
          {steps.map((step, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-gray-600 leading-relaxed">
              <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-accent/10 text-xs font-medium text-accent">
                {i + 1}
              </span>
              <span>{step}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
