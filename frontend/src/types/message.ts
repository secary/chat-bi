export interface SseEvent {
  type:
    | 'thinking'
    | 'text'
    | 'chart'
    | 'kpi_cards'
    | 'plan_summary'
    | 'analysis_proposal'
    | 'dashboard_ready'
    | 'error'
    | 'done';
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
  analysisProposal?: AnalysisProposal;
  dashboardReady?: DashboardReady;
  thinking?: string[];
  error?: string;
}

export interface AnalysisProposal {
  markdown: string;
  dataset: {
    row_count: number;
    domain_guess: string;
    domain_label?: string;
    confidence: number;
  };
  proposed_metrics: ProposedMetric[];
  actions: Array<{ id: string; label: string; kind: string }>;
  question: string;
}

export interface ProposedMetric {
  id: string;
  name: string;
  description: string;
  formula_md: string;
  matched_fields: Record<string, string>;
  chart_hint: string;
  confidence: number;
  selected: boolean;
}

export interface DashboardReady {
  markdown: string;
  title: string;
  dataset: {
    row_count: number;
    domain_guess: string;
    domain_label?: string;
  };
  widgets: Array<{ id: string; title: string; type: string; chart_index: number }>;
  charts: Record<string, unknown>[];
  metrics: Array<{ id: string; name: string; rows: Record<string, unknown>[] }>;
  kpi_values?: Array<{ label: string; value: string; unit: string; status: string }>;
  table_rows?: Record<string, string>[];
  table_columns?: string[];
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
