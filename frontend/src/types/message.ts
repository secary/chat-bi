export interface SseEvent {
  type: 'thinking' | 'text' | 'chart' | 'kpi_cards' | 'error' | 'done';
  content: unknown;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  chart?: Record<string, unknown>;
  kpiCards?: KpiCard[];
  thinking?: string[];
  error?: string;
}

export interface KpiCard {
  label: string;
  value: string;
  unit: string;
  status: 'success' | 'warning' | 'danger' | 'neutral';
}

export interface ChatRequest {
  message: string;
  history: { role: string; content: string }[];
}

export interface UploadedFile {
  filename: string;
  server_path: string;
  size: number;
}
