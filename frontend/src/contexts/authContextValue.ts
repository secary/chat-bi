import { createContext } from 'react';
import type { AppUser } from '../types/auth';

export interface AuthState {
  user: AppUser | null;
  ready: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

export const AuthContext = createContext<AuthState | null>(null);
