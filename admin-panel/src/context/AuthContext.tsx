import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { jwtDecode } from 'jwt-decode';

import api, { setAuthToken } from '../lib/api';

type AdminScope = 'system' | 'org';

interface JwtShape {
  exp?: number;
  roles?: string[];
  scope?: string;
  sub?: string;
}

interface AuthState {
  token: string | null;
  scope: AdminScope | null;
  roles: string[];
  username: string | null;
  expiresAt: number | null;
}

interface LoginPayload {
  username: string;
  password: string;
  scope: AdminScope;
}

interface LoginResponse {
  access_token?: string;
  token?: string;
  token_type?: string;
  expires_in?: number;
}

interface AuthContextValue extends AuthState {
  loading: boolean;
  error: string | null;
  login: (payload: LoginPayload) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const STORAGE_KEY = 'taskmate-admin-auth';

const loginEndpoints: Record<AdminScope, string> = {
  system: '/api/admin/auth/login',
  org: '/api/orgs/admin/login'
};

const fallbackRoles: Record<AdminScope, string[]> = {
  system: ['system_admin'],
  org: ['org_admin']
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider = ({ children }: AuthProviderProps) => {
  const [state, setState] = useState<AuthState>(() => {
    if (typeof window === 'undefined') {
      return { token: null, scope: null, roles: [], username: null, expiresAt: null };
    }

    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (!raw) {
        return { token: null, scope: null, roles: [], username: null, expiresAt: null };
      }
      const parsed: AuthState = JSON.parse(raw);
      if (parsed.token) {
        setAuthToken(parsed.token);
      }
      return parsed;
    } catch {
      return { token: null, scope: null, roles: [], username: null, expiresAt: null };
    }
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }, [state]);

  const logout = useCallback(() => {
    setAuthToken(null);
    setState({ token: null, scope: null, roles: [], username: null, expiresAt: null });
  }, []);

  useEffect(() => {
    if (!state.token || !state.expiresAt) return;
    const timeout = window.setTimeout(() => logout(), Math.max(state.expiresAt * 1000 - Date.now(), 0));
    return () => window.clearTimeout(timeout);
  }, [state.token, state.expiresAt, logout]);

  const login = useCallback(async ({ username, password, scope }: LoginPayload) => {
    setLoading(true);
    setError(null);

    try {
      const endpoint = loginEndpoints[scope];
      const payload = { username, password };
      let token: string | undefined;
      let expiresAt: number | null = null;

      try {
        const { data } = await api.post<LoginResponse>(endpoint, payload);
        token = data.access_token ?? data.token;
        if (data.expires_in) {
          expiresAt = Math.floor(Date.now() / 1000) + data.expires_in;
        }
      } catch (err) {
        if (import.meta.env.DEV) {
          token = window.btoa(`${scope}-${username}-${Date.now()}`);
          expiresAt = Math.floor(Date.now() / 1000) + 60 * 60 * 4;
        } else {
          throw err;
        }
      }

      if (!token) {
        throw new Error('Authentication failed: missing token response.');
      }

      const decoded = (() => {
        try {
          return jwtDecode<JwtShape>(token!);
        } catch {
          return {} as JwtShape;
        }
      })();

      const roles = decoded.roles ?? fallbackRoles[scope];
      const normalizedScope: AdminScope =
        decoded.scope === 'system_admin' ? 'system' : decoded.scope === 'org_admin' ? 'org' : scope;
      const finalExpiresAt = decoded.exp ?? expiresAt;

      setAuthToken(token);
      setState({
        token,
        scope: normalizedScope,
        roles,
        username,
        expiresAt: finalExpiresAt ?? null
      });
    } catch (err) {
      console.error(err);
      const message = err instanceof Error ? err.message : 'Unable to authenticate';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      ...state,
      loading,
      error,
      login,
      logout
    }),
    [state, loading, error, login, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
};
