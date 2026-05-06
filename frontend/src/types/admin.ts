export interface SessionRow {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
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

export interface LlmSettingsView {
  model: string | null;
  api_base: string | null;
  api_key_set: boolean;
  updated_at: string | null;
}
