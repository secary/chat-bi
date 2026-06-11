export interface SessionRow {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface SessionListApi {
  sessions: SessionRow[];
  suggested_prompts: string[];
}

export interface AdminSkillRow {
  slug: string;
  name: string;
  description: string;
  enabled: boolean;
}

export interface DbConnectionRow {
  id: number;
  name: string;
  host: string;
  port: number;
  username: string;
  database_name: string;
  is_default: boolean;
  created_at?: string | null;
}

export interface DbConnectionCurrent {
  source: 'saved_default' | 'env';
  id: number | null;
  name: string;
  host: string;
  port: number;
  username: string;
  database_name: string;
  is_default: boolean;
}

export interface DbConnectionPayload {
  name: string;
  host: string;
  port: number;
  username: string;
  password?: string;
  database_name: string;
  is_default: boolean;
}

export interface SkillAuditIssue {
  code: string;
  level: string;
  message: string;
}

export interface SkillAuditRow {
  slug: string;
  name: string;
  description: string;
  enabled: boolean;
  status: string;
  issue_count: number;
  issues: SkillAuditIssue[];
  script_count: number;
  test_count: number;
  has_skill_md: boolean;
  has_workflow: boolean;
  has_safety: boolean;
  trigger_count: number;
  required_context_count: number;
}

export interface LlmProfilePublic {
  id: number;
  display_name: string | null;
  model: string;
  api_base: string | null;
  api_key_set: boolean;
  is_env_default?: boolean;
  sort_order: number;
  health_status: string;
  health_detail: string | null;
  health_checked_at: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface LlmSettingsView {
  model: string | null;
  api_base: string | null;
  api_key_set: boolean;
  active_profile_id?: number | null;
  updated_at: string | null;
  profiles?: LlmProfilePublic[];
  effective_model?: string | null;
  effective_api_base?: string | null;
  effective_api_key_set?: boolean;
  effective_source?: 'saved_settings' | 'env';
}

export interface HarnessAuditIssue {
  code: string;
  level: string;
  message: string;
}

export interface HarnessAuditEvent {
  id: number;
  trace_id: string;
  span_name: string;
  event_name: string;
  level: string;
  message: string;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface HarnessBusinessFlowStep {
  key: string;
  label: string;
  status: string;
  detail: string;
}

export interface HarnessBusinessFlowCard {
  flow_key: string;
  title: string;
  status: string;
  summary: string;
  steps: HarnessBusinessFlowStep[];
}

export interface HarnessAuditReport {
  trace_id: string;
  status: string;
  score: number;
  summary: string;
  issues: HarnessAuditIssue[];
  business_flows: HarnessBusinessFlowCard[];
  events: HarnessAuditEvent[];
  event_count: number;
}

export interface HarnessAuditCandidate {
  trace_id: string;
  last_seen: string;
  event_count: number;
}
