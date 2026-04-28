import { useState } from 'react';

interface ThinkingBubbleProps {
  steps: string[];
}

export function ThinkingBubble({ steps }: ThinkingBubbleProps) {
  const [collapsed, setCollapsed] = useState(false);

  if (steps.length === 0) return null;

  return (
    <div className="mb-3 rounded-lg border border-gray-200 bg-gray-50 px-4 py-2">
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
      >
        <span className="text-xs">{collapsed ? '▶' : '▼'}</span>
        <span>思考步骤 ({steps.length})</span>
      </button>
      {!collapsed && (
        <ul className="mt-2 space-y-1">
          {steps.map((step, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-gray-600">
              <span className="mt-0.5 h-4 w-4 shrink-0 rounded-full bg-blue-100 text-center text-xs leading-4 text-blue-600">
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
