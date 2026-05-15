import { useRef, useState } from 'react';
import { newTraceId, uploadFile } from '../api/client';

interface ChatInputProps {
  onSend: (text: string, traceId?: string) => void;
  onAbort?: () => void;
  loading: boolean;
  disabled?: boolean;
}

export function ChatInput({ onSend, onAbort, loading, disabled = false }: ChatInputProps) {
  const [message, setMessage] = useState('');
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [pendingTraceId, setPendingTraceId] = useState<string>();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (loading && onAbort) {
      onAbort();
      return;
    }
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
        : `请读取我上传的文件 ${uploaded.server_path}，先校验结构；如果符合现有业务表就直接分析，不符合就按通用表分析`;
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
      className={`rounded-2xl border p-4 shadow-card transition-shadow focus-within:shadow-card-hover ${
        dragging ? 'border-accent bg-accent-light' : 'border-gray-200 bg-surface'
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
          className="h-11 shrink-0 rounded-xl border border-gray-200 bg-white px-4 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 disabled:opacity-50 disabled:bg-gray-100"
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
          className="h-11 min-w-0 flex-1 rounded-xl border border-gray-200 bg-surface px-4 text-sm transition-all focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent disabled:opacity-50 disabled:bg-gray-100"
        />
        <button
          type="submit"
          disabled={loading || uploading || !message.trim() || disabled}
          className={`h-11 shrink-0 rounded-xl px-5 text-sm font-medium transition-colors active:scale-[0.97] ${
            loading
              ? 'bg-red-500 text-white hover:bg-red-600'
              : 'bg-accent text-white hover:bg-accent-hover'
          } disabled:opacity-50 disabled:bg-gray-300`}
        >
          {loading ? '中止' : '发送'}
        </button>
      </div>
      <div
        className={`mt-2 text-xs ${
          uploadError ? 'text-red-600' : dragging ? 'text-accent' : 'text-gray-400'
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
