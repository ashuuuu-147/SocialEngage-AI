import React, { useState } from 'react';
import { KeyRound, Mail, ShieldCheck, Sparkles, Terminal } from 'lucide-react';
import { DEFAULT_DEV_USER_ID, useAuth } from '../lib/auth';
import { getSupabaseClient, isDevAuthAllowed, isSupabaseConfigured } from '../lib/supabase';

type AuthTab = 'supabase' | 'dev' | 'jwt';

export function AuthPage() {
  const { signInDevWorkspace, signInWithJwt, enterDemoPreview } = useAuth();
  const [devUserId, setDevUserId] = useState(DEFAULT_DEV_USER_ID);
  const [jwtToken, setJwtToken] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [authMode, setAuthMode] = useState<'signin' | 'signup' | 'magic'>('signin');
  const [authMessage, setAuthMessage] = useState<string | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const [tab, setTab] = useState<AuthTab>(
    isSupabaseConfigured ? 'supabase' : isDevAuthAllowed ? 'dev' : 'jwt'
  );

  function handleDevSubmit(e: React.FormEvent) {
    e.preventDefault();
    signInDevWorkspace(devUserId, 'Demo Workspace (Dev API)');
  }

  function handleJwtSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!jwtToken.trim()) return;
    signInWithJwt(jwtToken.trim(), 'Supabase Session');
  }

  async function handleSupabaseSubmit(e: React.FormEvent) {
    e.preventDefault();
    const supabase = getSupabaseClient();
    if (!supabase) return;

    setSubmitting(true);
    setAuthError(null);
    setAuthMessage(null);
    try {
      if (authMode === 'magic') {
        const { error } = await supabase.auth.signInWithOtp({
          email: email.trim(),
          options: { emailRedirectTo: window.location.origin },
        });
        if (error) throw error;
        setAuthMessage('Check your email for the one-click sign-in link.');
      } else if (authMode === 'signup') {
        const { data, error } = await supabase.auth.signUp({
          email: email.trim(),
          password,
        });
        if (error) throw error;
        if (data.session) {
          signInWithJwt(data.session.access_token, data.session.user.email || 'Supabase User');
        } else {
          setAuthMessage('Account created! Check your inbox to confirm your email.');
        }
      } else {
        const { data, error } = await supabase.auth.signInWithPassword({
          email: email.trim(),
          password,
        });
        if (error) throw error;
        if (data.session) {
          signInWithJwt(data.session.access_token, data.session.user.email || 'Supabase User');
        }
      }
    } catch (err) {
      setAuthError(err instanceof Error ? err.message : 'Authentication failed.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="row-wrap" style={{ gap: 12 }}>
          <span className="brand-mark" aria-hidden="true">
            <Sparkles size={20} />
          </span>
          <div>
            <h1 className="page-title" style={{ fontSize: 24 }}>
              SocialEngage AI
            </h1>
            <p className="meta-text">Meaningful engagement, made easier.</p>
          </div>
        </div>

        <div className="info-banner">
          <ShieldCheck size={18} style={{ flexShrink: 0, marginTop: 2 }} aria-hidden="true" />
          <div style={{ fontSize: 13 }}>
            <strong>Human-in-the-loop by design.</strong> SocialEngage AI monitors authorized
            sources and drafts thoughtful replies for your review—nothing is ever auto-posted.
          </div>
        </div>

        <div className="tab-pills" role="tablist" aria-label="Sign in method">
          {isSupabaseConfigured && (
            <button
              type="button"
              role="tab"
              aria-selected={tab === 'supabase'}
              className={`tab-pill ${tab === 'supabase' ? 'is-active' : ''}`}
              onClick={() => setTab('supabase')}
            >
              <Mail size={13} style={{ marginRight: 5, verticalAlign: 'middle' }} aria-hidden="true" />
              Account Sign In
            </button>
          )}
          {isDevAuthAllowed && (
            <button
              type="button"
              role="tab"
              aria-selected={tab === 'dev'}
              className={`tab-pill ${tab === 'dev' ? 'is-active' : ''}`}
              onClick={() => setTab('dev')}
            >
              <Terminal size={13} style={{ marginRight: 5, verticalAlign: 'middle' }} aria-hidden="true" />
              Dev Workspace (X-Dev-User-Id)
            </button>
          )}
          <button
            type="button"
            role="tab"
            aria-selected={tab === 'jwt'}
            className={`tab-pill ${tab === 'jwt' ? 'is-active' : ''}`}
            onClick={() => setTab('jwt')}
          >
            <KeyRound size={13} style={{ marginRight: 5, verticalAlign: 'middle' }} aria-hidden="true" />
            Supabase Bearer JWT
          </button>
        </div>

        {tab === 'supabase' && isSupabaseConfigured ? (
          <form className="stack-md" onSubmit={handleSupabaseSubmit}>
            <div className="row-wrap" style={{ gap: 8 }}>
              <button
                type="button"
                className={`btn btn-sm ${authMode === 'signin' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setAuthMode('signin')}
              >
                Sign In
              </button>
              <button
                type="button"
                className={`btn btn-sm ${authMode === 'signup' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setAuthMode('signup')}
              >
                Create Account
              </button>
              <button
                type="button"
                className={`btn btn-sm ${authMode === 'magic' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setAuthMode('magic')}
              >
                Magic Link
              </button>
            </div>

            {authError && (
              <div className="error-banner" role="alert">
                <div className="error-banner-body">
                  <strong>Sign-in error</strong>
                  <span>{authError}</span>
                </div>
              </div>
            )}

            {authMessage && (
              <div className="info-banner" role="status">
                <span>{authMessage}</span>
              </div>
            )}

            <div className="field">
              <label htmlFor="auth-email" className="field-label">
                Email Address
              </label>
              <input
                id="auth-email"
                type="email"
                className="input"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            {authMode !== 'magic' && (
              <div className="field">
                <label htmlFor="auth-password" className="field-label">
                  Password
                </label>
                <input
                  id="auth-password"
                  type="password"
                  className="input"
                  minLength={6}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>
            )}

            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting
                ? 'Please wait...'
                : authMode === 'magic'
                  ? 'Send Magic Link'
                  : authMode === 'signup'
                    ? 'Create Account'
                    : 'Sign In'}
            </button>
          </form>
        ) : tab === 'dev' && isDevAuthAllowed ? (
          <form className="stack-md" onSubmit={handleDevSubmit}>
            <div className="field">
              <label htmlFor="dev-user-id" className="field-label">
                Dev Workspace User UUID
              </label>
              <input
                id="dev-user-id"
                type="text"
                className="input"
                value={devUserId}
                onChange={(e) => setDevUserId(e.target.value)}
                required
              />
              <span className="field-hint">
                Connects to the live REST API using the <code>X-Dev-User-Id</code> header when
                dev auth bypass is enabled on the API server.
              </span>
            </div>
            <button type="submit" className="btn btn-primary">
              Continue with Demo Workspace
            </button>
          </form>
        ) : (
          <form className="stack-md" onSubmit={handleJwtSubmit}>
            <div className="field">
              <label htmlFor="supabase-jwt" className="field-label">
                Supabase Access Token (Bearer JWT)
              </label>
              <textarea
                id="supabase-jwt"
                className="textarea"
                rows={3}
                placeholder="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
                value={jwtToken}
                onChange={(e) => setJwtToken(e.target.value)}
                required
              />
              <span className="field-hint">
                Sent as <code>Authorization: Bearer &lt;token&gt;</code> on every API request.
              </span>
            </div>
            <button type="submit" className="btn btn-primary" disabled={!jwtToken.trim()}>
              Sign In with Token
            </button>
          </form>
        )}

        {isDevAuthAllowed && (
          <div
            style={{
              borderTop: '1px solid var(--color-border)',
              paddingTop: 16,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: 12,
              flexWrap: 'wrap',
            }}
          >
            <span className="meta-text">Backend API offline or testing UI locally?</span>
            <button type="button" className="btn btn-secondary btn-sm" onClick={enterDemoPreview}>
              Preview UI Offline (Demo Data)
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
