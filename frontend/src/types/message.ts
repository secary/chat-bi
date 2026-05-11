export interface SseEvent {
  type: 'thinking' | 'text' | 'chart' | 'kpi_cards' | 'plan_summary' | 'error' | 'done';
  content: unknown;
}

export interface PlanSummary {
  metric: string;
  metric_code: string;
  source_table: string;
  dimensions: string[];
  filters: Array<{ dimension: string; value: string }>;
  time_filter: string | null;
  order_by_metric_desc: boolean;
  limit: number | null;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  chart?: Record<string, unknown>;
  kpiCards?: KpiCard[];
  planSummary?: PlanSummary;
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
  session_id?: number;
  db_connection_id?: number;
  multi_agents?: boolean;
}

export interface UploadedFile {
  filename: string;
  server_path: string;
  size: number;
  trace_id: string;
}
