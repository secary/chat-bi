import { useRef, useState } from 'react';
import { newTraceId, uploadFile } from '../api/client';

interface ChatInputProps {
  onSend: (text: string, traceId?: string) => void;
  loading: boolean;
  disabled?: boolean;
}

export function ChatInput({ onSend, loading, disabled = false }: ChatInputProps) {
  const [message, setMessage] = useState('');
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [pendingTraceId, setPendingTraceId] = useState<string>();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (message.trim() && !loading && !uploading && !disabled) {
      onSend(message, pendingTraceId);
      setMessage('');
      setPendingTraceId(undefined);
    }
  };

  const attachFile = async (file: File) => {
    if (loading || uploading || disabled) return;
    setUploadError('');
    setUploading(true);
    const traceId = newTraceId();
    try {
      const uploaded = await uploadFile(file, traceId);
      const isImage = /\.(png|jpg|jpeg|webp)$/i.test(file.name);
      const prompt = isImage
        ? `请读取我上传的图像 ${uploaded.server_path}，纳入分析`
        : `请读取我上传的文件 ${uploaded.server_path}，按数据库表结构校验`;
      setMessage((current) => (current.trim() ? `${current.trim()}\n${prompt}` : prompt));
      setPendingTraceId(uploaded.trace_id || traceId);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : String(err));
    } finally {
      setUploading(false);
    }
  };

  const handleFiles = (files: FileList | null) => {
    const file = files?.[0];
    if (file) void attachFile(file);
  };

  return (
    <form
      onSubmit={handleSubmit}
      onDragEnter={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget as Node)) setDragging(false);
      }}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        handleFiles(e.dataTransfer.files);
      }}
      className={`rounded-2xl border p-4 shadow-sm transition ${
        dragging ? 'border-blue-300 bg-blue-50/80' : 'border-gray-200 bg-white'
      }`}
    >
      <div className="flex items-center gap-2">
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,.xlsx,.xlsm,.png,.jpg,.jpeg,.webp"
          className="hidden"
          onChange={(e) => {
            handleFiles(e.target.files);
            e.target.value = '';
          }}
        />
        <button
          type="button"
          disabled={loading || uploading || disabled}
          onClick={() => fileInputRef.current?.click()}
          className="h-11 shrink-0 rounded-full border border-gray-300 bg-white px-4 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:bg-gray-100 disabled:text-gray-400"
          title="上传 CSV、Excel 或图像"
        >
          {uploading ? '上传中' : '附件'}
        </button>
        <input
          name="message"
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="输入业务问题，或拖入 CSV/Excel/图像..."
          disabled={loading || uploading || disabled}
          className="h-11 min-w-0 flex-1 rounded-full border border-gray-300 bg-white px-5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
        />
        <button
          type="submit"
          disabled={loading || uploading || !message.trim() || disabled}
          className="h-11 shrink-0 rounded-full bg-blue-600 px-6 text-sm font-medium text-white hover:bg-blue-700 disabled:bg-gray-400"
        >
          {loading ? '处理中' : '发送'}
        </button>
      </div>
      <div
        className={`mt-2 text-xs ${
          uploadError ? 'text-red-600' : dragging ? 'text-blue-700' : 'text-gray-500'
        }`}
      >
        {uploadError ||
          (dragging
            ? '松开即可上传文件'
            : '支持 CSV、XLSX、XLSM 与 PNG/JPG/WebP，可直接拖到输入框区域')}
      </div>
    </form>
  );
}
