import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { createApiClient, type ApiClient, type AuthCredentials } from './api';
import { getSupabaseClient, isDevAuthAllowed } from './supabase';

export const DEFAULT_DEV_USER_ID = '00000000-0000-0000-0000-000000000001';
const STORAGE_KEY = 'socialengage_auth_session_v1';

export interface AuthSession extends AuthCredentials {
  label: string;
}

interface AuthContextValue {
  session: AuthSession | null;
  api: ApiClient;
  signInWithJwt: (token: string, label?: string) => void;
  signInDevWorkspace: (userId?: string, label?: string) => void;
  enterDemoPreview: () => void;
  signOut: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function loadStoredSession(): AuthSession | null {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as AuthSession;
    if (parsed && parsed.mode === 'jwt') {
      return parsed;
    }
    if (parsed && (parsed.mode === 'dev' || parsed.mode === 'demo') && isDevAuthAllowed) {
      return parsed;
    }
    return null;
  } catch {
    return null;
  }
}

export function AuthProvider({
  children,
  initialSession,
}: {
  children: React.ReactNode;
  initialSession?: AuthSession | null;
}) {
  const [session, setSession] = useState<AuthSession | null>(() =>
    initialSession !== undefined ? initialSession : loadStoredSession()
  );

  const sessionRef = useRef<AuthSession | null>(session);
  sessionRef.current = session;

  const persist = useCallback((next: AuthSession | null) => {
    sessionRef.current = next;
    setSession(next);
    try {
      if (next) {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      } else {
        window.localStorage.removeItem(STORAGE_KEY);
      }
    } catch {
      // Ignore storage errors in restricted environments
    }
  }, []);

  // Sync live Supabase Auth session (email/password, magic link, token refresh)
  useEffect(() => {
    if (initialSession !== undefined) return;
    const supabase = getSupabaseClient();
    if (!supabase) return;

    let mounted = true;
    supabase.auth.getSession().then(({ data }) => {
      if (!mounted || !data.session) return;
      persist({
        mode: 'jwt',
        token: data.session.access_token,
        label: data.session.user.email || 'Supabase User',
      });
    });

    const { data: sub } = supabase.auth.onAuthStateChange((_event, supaSession) => {
      if (!mounted) return;
      if (supaSession) {
        persist({
          mode: 'jwt',
          token: supaSession.access_token,
          label: supaSession.user.email || 'Supabase User',
        });
      } else if (sessionRef.current?.mode === 'jwt') {
        persist(null);
      }
    });

    return () => {
      mounted = false;
      sub.subscription.unsubscribe();
    };
  }, [initialSession, persist]);

  const api = useMemo(
    () =>
      createApiClient(() => {
        const s = sessionRef.current;
        if (!s) return null;
        return { mode: s.mode, token: s.token, devUserId: s.devUserId };
      }),
    []
  );

  const signInWithJwt = useCallback(
    (token: string, label = 'Authenticated User') => {
      persist({ mode: 'jwt', token: token.trim(), label });
    },
    [persist]
  );

  const signInDevWorkspace = useCallback(
    (userId = DEFAULT_DEV_USER_ID, label = 'Demo Workspace (Dev API)') => {
      persist({ mode: 'dev', devUserId: userId.trim() || DEFAULT_DEV_USER_ID, label });
    },
    [persist]
  );

  const enterDemoPreview = useCallback(() => {
    api.resetDemoStore();
    persist({ mode: 'demo', label: 'Offline Demo Preview' });
  }, [api, persist]);

  const signOut = useCallback(() => {
    const supabase = getSupabaseClient();
    if (supabase) {
      void supabase.auth.signOut();
    }
    persist(null);
  }, [persist]);

  const value = useMemo<AuthContextValue>(
    () => ({
      session,
      api,
      signInWithJwt,
      signInDevWorkspace,
      enterDemoPreview,
      signOut,
    }),
    [session, api, signInWithJwt, signInDevWorkspace, enterDemoPreview, signOut]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used inside AuthProvider');
  }
  return ctx;
}
