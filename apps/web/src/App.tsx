import { useCallback, useEffect, useState } from 'react';
import { AppShell } from './components/AppShell';
import { ManualPostModal } from './components/ManualPostModal';
import { ToastProvider, useToast } from './components/Toast';
import { AuthProvider, useAuth, type AuthSession } from './lib/auth';
import type { NavSection, Target } from './lib/types';
import { ActivityPage } from './pages/ActivityPage';
import { AuthPage } from './pages/AuthPage';
import { DraftsPage } from './pages/DraftsPage';
import { InboxPage } from './pages/InboxPage';
import { OverviewPage } from './pages/OverviewPage';
import { SettingsPage } from './pages/SettingsPage';
import { WatchlistPage } from './pages/WatchlistPage';

const PAGE_META: Record<NavSection, { title: string; subtitle: string }> = {
  overview: {
    title: 'Overview',
    subtitle: 'Workspace pulse, pending comment drafts, and source health',
  },
  watchlist: {
    title: 'Watchlist',
    subtitle: 'Manage creator profiles and authorized monitoring sources',
  },
  inbox: {
    title: 'Post Inbox',
    subtitle: 'Review newly detected and submitted posts before drafting',
  },
  drafts: {
    title: 'Draft Review',
    subtitle: 'Edit, copy, and open posts—human review required for every comment',
  },
  activity: {
    title: 'Activity',
    subtitle: 'Transparent source checks, skipped items, and monitoring jobs',
  },
  settings: {
    title: 'Settings',
    subtitle: 'Comment style, Telegram alerts, cadence, and privacy controls',
  },
};

function WorkspaceApp() {
  const { session, api, signOut, enterDemoPreview } = useAuth();
  const { showToast } = useToast();

  const [section, setSection] = useState<NavSection>('overview');
  const [submitModalOpen, setSubmitModalOpen] = useState(false);
  const [submitInitialTargetId, setSubmitInitialTargetId] = useState<string | undefined>(undefined);
  const [targets, setTargets] = useState<Target[]>([]);
  const [pendingDraftsCount, setPendingDraftsCount] = useState(0);
  const [connectionStatus, setConnectionStatus] = useState<'online' | 'demo' | 'offline'>('online');
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const bumpRefresh = useCallback(() => {
    setRefreshTrigger((n) => n + 1);
  }, []);

  const syncShellState = useCallback(async () => {
    if (!session) return;
    if (session.mode === 'demo') {
      setConnectionStatus('demo');
    }
    try {
      const [overview, targetList] = await Promise.all([
        api.getOverview(),
        api.listTargets({ limit: 100 }),
      ]);
      setPendingDraftsCount(overview.drafts_awaiting_review);
      setTargets(targetList);
      if (session.mode !== 'demo') {
        setConnectionStatus('online');
      }
    } catch {
      if (session.mode !== 'demo') {
        setConnectionStatus('offline');
      }
    }
  }, [api, session]);

  useEffect(() => {
    void syncShellState();
  }, [syncShellState, refreshTrigger]);

  if (!session) {
    return <AuthPage />;
  }

  const meta = PAGE_META[section];
  const authModeLabel =
    session.mode === 'demo'
      ? 'Offline Preview'
      : session.mode === 'dev'
        ? 'Dev X-Dev-User-Id'
        : 'Supabase JWT';

  function openSubmitPost(targetId?: string) {
    setSubmitInitialTargetId(targetId);
    setSubmitModalOpen(true);
  }

  return (
    <>
      <AppShell
        activeSection={section}
        onNavigate={setSection}
        pageTitle={meta.title}
        pageSubtitle={meta.subtitle}
        pendingDraftsCount={pendingDraftsCount}
        connectionStatus={connectionStatus}
        accountLabel={session.label}
        authModeLabel={authModeLabel}
        onSignOut={signOut}
        onOpenSubmitPost={() => openSubmitPost()}
      >
        {connectionStatus === 'demo' && (
          <div className="info-banner" role="status">
            <div className="row-between" style={{ width: '100%' }}>
              <span style={{ fontSize: 13 }}>
                <strong>Offline Demo Preview active:</strong> Changes stay in browser memory. Sign
                out to connect to the live REST API.
              </span>
              <button type="button" className="btn btn-secondary btn-sm" onClick={signOut}>
                Switch to Live API
              </button>
            </div>
          </div>
        )}

        {connectionStatus === 'offline' && (
          <div className="error-banner" role="alert">
            <div style={{ fontSize: 13 }}>
              <strong>API Server Unreachable:</strong> Could not connect to the backend REST API.
              Start the FastAPI server or switch to Offline Demo Preview.
            </div>
            <div className="row-wrap" style={{ gap: 8 }}>
              <button type="button" className="btn btn-secondary btn-sm" onClick={bumpRefresh}>
                Retry
              </button>
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={enterDemoPreview}
              >
                Use Demo Preview
              </button>
            </div>
          </div>
        )}

        {section === 'overview' && (
          <OverviewPage
            onNavigate={setSection}
            onOpenSubmitPost={() => openSubmitPost()}
            refreshTrigger={refreshTrigger}
          />
        )}
        {section === 'watchlist' && (
          <WatchlistPage
            onOpenSubmitPostForTarget={(targetId) => openSubmitPost(targetId)}
            onTargetsChanged={bumpRefresh}
          />
        )}
        {section === 'inbox' && (
          <InboxPage
            onOpenSubmitPost={() => openSubmitPost()}
            onNavigate={setSection}
            refreshTrigger={refreshTrigger}
          />
        )}
        {section === 'drafts' && (
          <DraftsPage
            onOpenSubmitPost={() => openSubmitPost()}
            onDraftsChanged={bumpRefresh}
            refreshTrigger={refreshTrigger}
          />
        )}
        {section === 'activity' && <ActivityPage />}
        {section === 'settings' && <SettingsPage />}
      </AppShell>

      <ManualPostModal
        open={submitModalOpen}
        targets={targets}
        initialTargetId={submitInitialTargetId}
        onClose={() => setSubmitModalOpen(false)}
        onSubmitManual={(payload) => api.ingestManualPost(payload)}
        onSuccess={(post) => {
          bumpRefresh();
          showToast(
            post.drafts.length > 0
              ? `Post saved with ${post.drafts.length} draft(s) ready for review.`
              : 'Post added to your Inbox.',
            'success'
          );
        }}
      />
    </>
  );
}

export function App({ initialSession }: { initialSession?: AuthSession | null } = {}) {
  return (
    <AuthProvider initialSession={initialSession}>
      <ToastProvider>
        <WorkspaceApp />
      </ToastProvider>
    </AuthProvider>
  );
}

export default App;
