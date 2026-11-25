import React, { useState } from 'react';
import type { NavSection } from '../lib/types';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';

interface AppShellProps {
  activeSection: NavSection;
  onNavigate: (section: NavSection) => void;
  pageTitle: string;
  pageSubtitle?: string;
  pendingDraftsCount?: number;
  connectionStatus: 'online' | 'demo' | 'offline';
  accountLabel: string;
  authModeLabel: string;
  onSignOut: () => void;
  onOpenSubmitPost: () => void;
  children: React.ReactNode;
}

export function AppShell({
  activeSection,
  onNavigate,
  pageTitle,
  pageSubtitle,
  pendingDraftsCount = 0,
  connectionStatus,
  accountLabel,
  authModeLabel,
  onSignOut,
  onOpenSubmitPost,
  children,
}: AppShellProps) {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="app-shell">
      {mobileOpen && (
        <div
          className="drawer-backdrop"
          aria-hidden="true"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <Sidebar
        activeSection={activeSection}
        onNavigate={onNavigate}
        mobileOpen={mobileOpen}
        onCloseMobile={() => setMobileOpen(false)}
        pendingDraftsCount={pendingDraftsCount}
        connectionStatus={connectionStatus}
        accountLabel={accountLabel}
        authModeLabel={authModeLabel}
        onSignOut={onSignOut}
      />

      <div className="app-main">
        <Topbar
          title={pageTitle}
          subtitle={pageSubtitle}
          onOpenMobileMenu={() => setMobileOpen(true)}
          onOpenSubmitPost={onOpenSubmitPost}
        />

        <main className="content-container" id="main-content">
          {children}
        </main>
      </div>
    </div>
  );
}
