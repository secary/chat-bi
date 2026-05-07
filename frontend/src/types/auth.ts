export interface AppUser {
  id: number;
  username: string;
  role: string;
}

export interface AppUserRow {
  id: number;
  username: string;
  role: string;
  is_active: number | boolean;
  created_at: string;
}
