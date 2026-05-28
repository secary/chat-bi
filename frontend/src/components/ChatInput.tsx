import { useRef, useState } from 'react';
import { newTraceId, uploadFile } from '../api/client';
import type { UploadedFile } from '../types/message';

interface ChatInputProps {
  onSend: (text: string, traceId?: string, uploads?: UploadedFile[]) => void;
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
  const [pendingUpload, setPendingUpload] = useState<UploadedFile>();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (loading && onAbort) {
      onAbort();
      return;
    }
    if (message.trim() && !loading && !uploading && !disabled) {
      onSend(message.trim(), pendingTraceId, pendingUpload ? [pendingUpload] : undefined);
      setMessage('');
      setPendingTraceId(undefined);
      setPendingUpload(undefined);
    }
  };

  const attachFile = async (file: File) => {
    if (loading || uploading || disabled) return;
    setUploadError('');
    setUploading(true);
    const traceId = newTraceId();
    try {
      const uploaded = await uploadFile(file, traceId);
      setPendingUpload(uploaded);
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
      {pendingUpload ? (
        <div className="mb-3 flex min-w-0 items-center justify-between gap-3 rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-900">
          <div className="min-w-0">
            <span className="font-medium">已上传</span>
            <span className="ml-2 inline-block max-w-full truncate align-bottom">
              {pendingUpload.filename}
            </span>
          </div>
          <button
            type="button"
            className="shrink-0 rounded-lg border border-emerald-200 bg-white px-2 py-1 text-emerald-800 transition-colors hover:bg-emerald-100"
            onClick={() => {
              setPendingUpload(undefined);
              setPendingTraceId(undefined);
            }}
          >
            移除
          </button>
        </div>
      ) : null}
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
          placeholder={pendingUpload ? '针对已上传附件输入你的问题...' : '输入业务问题，或拖入 CSV/Excel/图像...'}
          disabled={loading || uploading || disabled}
          className="h-11 min-w-0 flex-1 rounded-xl border border-gray-200 bg-surface px-4 text-sm transition-all focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent disabled:opacity-50 disabled:bg-gray-100"
        />
        <button
          type="submit"
          disabled={loading ? false : (uploading || !message.trim() || disabled)}
          onClick={loading ? undefined : undefined}
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
            : pendingUpload
              ? '附件会随下一条消息一起发送'
              : '支持 CSV、XLSX、XLSM 与 PNG/JPG/WebP，可直接拖到输入框区域')}
      </div>
    </form>
  );
}
