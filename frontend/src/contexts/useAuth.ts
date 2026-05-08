import { useContext } from 'react';
import { AuthContext, type AuthState } from './authContextValue';

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('AuthProvider missing');
  return ctx;
}
