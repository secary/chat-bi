import { useRef, useEffect } from 'react';
import { useChat } from './hooks/useChat';
import { MessageBubble } from './components/MessageBubble';
import { ChatInput } from './components/ChatInput';

function App() {
  const { messages, loading, sendMessage, clearMessages } = useChat();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="flex h-screen flex-col bg-gray-100">
      <header className="flex items-center justify-between border-b border-gray-200 bg-white px-6 py-3">
        <div>
          <h1 className="text-lg font-semibold text-gray-900">零眸智能 ChatBI</h1>
          <p className="text-xs text-gray-500">对话式数据分析</p>
        </div>
        <button
          onClick={clearMessages}
          className="rounded-md border border-gray-300 px-3 py-1 text-xs text-gray-600 hover:bg-gray-50"
        >
          清空对话
        </button>
      </header>

      <main className="flex-1 overflow-y-auto px-4 py-6">
        <div className="mx-auto max-w-3xl">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center pt-20 text-gray-400">
              <p className="text-4xl mb-2">📊</p>
              <p className="text-sm">输入业务问题开始分析</p>
              <p className="mt-1 text-xs">例如：1-4月销售额排行</p>
            </div>
          )}
          {messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))}
          <div ref={bottomRef} />
        </div>
      </main>

      <div className="mx-auto w-full max-w-3xl">
        <ChatInput onSend={sendMessage} loading={loading} />
      </div>
    </div>
  );
}

export default App;
