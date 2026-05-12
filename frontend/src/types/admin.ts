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
  is_default: number | boolean;
  created_at: string;
}

export interface CurrentDbConnectionView {
  source: 'saved_default' | 'env';
  id: number | null;
  name: string;
  host: string;
  port: number;
  username: string;
  database_name: string;
  is_default: boolean;
}

/** 多专线（Multi-Agent）registry 与 PUT /admin/multi-agents 请求体 */
export interface MultiAgentLineEntry {
  label: string;
  role_prompt: string;
  skills: string[];
}

export interface MultiAgentsRegistryPayload {
  max_agents_per_round: number;
  agents: Record<string, MultiAgentLineEntry>;
}

export interface LlmProfilePublic {
  id: number;
  display_name: string | null;
  model: string;
  api_base: string | null;
  api_key_set: boolean;
  sort_order: number;
  supports_vision: boolean;
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
  vision_profile_id?: number | null;
  vision_extract_enabled?: boolean;
  vision_disabled_by_env?: boolean;
  updated_at: string | null;
  profiles?: LlmProfilePublic[];
  effective_model?: string | null;
  effective_api_base?: string | null;
  effective_api_key_set?: boolean;
  effective_source?: 'saved_settings' | 'env';
}
