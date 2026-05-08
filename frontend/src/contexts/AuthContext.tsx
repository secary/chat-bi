import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import type { AppUser } from '../types/auth';
import { getMeApi, getStoredToken, loginApi, setStoredToken } from '../api/client';
import { authEnabled } from '../lib/authFlags';
import { devAuthFallbackAdmin } from '../lib/devAuthDefaults';
import { AuthContext } from './authContextValue';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AppUser | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!authEnabled) {
      void getMeApi()
        .then(setUser)
        .catch(() => setUser(devAuthFallbackAdmin))
        .finally(() => setReady(true));
      return;
    }
    const token = getStoredToken();
    if (!token) {
      queueMicrotask(() => setReady(true));
      return;
    }
    void getMeApi()
      .then(setUser)
      .catch(() => {
        setStoredToken(null);
        setUser(null);
      })
      .finally(() => setReady(true));
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const token = await loginApi(username, password);
    setStoredToken(token);
    const me = await getMeApi();
    setUser(me);
  }, []);

  const logout = useCallback(() => {
    setStoredToken(null);
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({
      user,
      ready,
      login,
      logout,
    }),
    [user, ready, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
