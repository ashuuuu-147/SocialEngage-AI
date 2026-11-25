import {
  Activity,
  BookmarkCheck,
  Inbox,
  LayoutDashboard,
  LogOut,
  MessageSquareText,
  Settings,
  Sparkles,
  Wifi,
  WifiOff,
  X,
} from 'lucide-react';
import type { NavSection } from '../lib/types';

interface SidebarProps {
  activeSection: NavSection;
  onNavigate: (section: NavSection) => void;
  mobileOpen: boolean;
  onCloseMobile: () => void;
  pendingDraftsCount?: number;
  connectionStatus: 'online' | 'demo' | 'offline';
  accountLabel: string;
  authModeLabel: string;
  onSignOut: () => void;
}

const NAV_ITEMS: Array<{ id: NavSection; label: string; icon: typeof LayoutDashboard }> = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'watchlist', label: 'Watchlist', icon: BookmarkCheck },
  { id: 'inbox', label: 'Post Inbox', icon: Inbox },
  { id: 'drafts', label: 'Drafts', icon: MessageSquareText },
  { id: 'activity', label: 'Activity', icon: Activity },
  { id: 'settings', label: 'Settings', icon: Settings },
];

export function Sidebar({
  activeSection,
  onNavigate,
  mobileOpen,
  onCloseMobile,
  pendingDraftsCount = 0,
  connectionStatus,
  accountLabel,
  authModeLabel,
  onSignOut,
}: SidebarProps) {
  const statusClass =
    connectionStatus === 'online'
      ? 'is-online'
      : connectionStatus === 'demo'
        ? 'is-demo'
        : 'is-offline';

  const statusText =
    connectionStatus === 'online'
      ? 'API Connected'
      : connectionStatus === 'demo'
        ? 'Demo Preview (Offline)'
        : 'API Unreachable';

  return (
    <aside
      className={`sidebar ${mobileOpen ? 'is-open' : ''}`}
      aria-label="Primary navigation"
    >
      <div className="sidebar-brand">
        <span className="brand-mark" aria-hidden="true">
          <Sparkles size={18} />
        </span>
        <div className="brand-text">
          <span className="brand-name">SocialEngage AI</span>
          <span className="brand-tagline">Meaningful engagement</span>
        </div>
        {mobileOpen && (
          <button
            type="button"
            className="btn btn-ghost btn-icon mobile-menu-btn"
            style={{ marginLeft: 'auto' }}
            onClick={onCloseMobile}
            aria-label="Close navigation menu"
          >
            <X size={18} aria-hidden="true" />
          </button>
        )}
      </div>

      <nav className="sidebar-nav" aria-label="Workspace sections">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = activeSection === item.id;
          return (
            <button
              key={item.id}
              type="button"
              className={`nav-item ${isActive ? 'is-active' : ''}`}
              aria-current={isActive ? 'page' : undefined}
              onClick={() => {
                onNavigate(item.id);
                onCloseMobile();
              }}
            >
              <Icon size={18} aria-hidden="true" />
              <span className="nav-label">{item.label}</span>
              {item.id === 'drafts' && pendingDraftsCount > 0 && (
                <span className="nav-badge" aria-label={`${pendingDraftsCount} drafts awaiting review`}>
                  {pendingDraftsCount}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        <div className={`connection-pill ${statusClass}`} role="status">
          {connectionStatus === 'offline' ? (
            <WifiOff size={14} aria-hidden="true" />
          ) : (
            <Wifi size={14} aria-hidden="true" />
          )}
          <span className="connection-text">{statusText}</span>
        </div>

        <div className="account-card">
          <div className="account-meta">
            <span className="account-name">{accountLabel}</span>
            <span className="account-mode">{authModeLabel}</span>
          </div>
          <button
            type="button"
            className="btn btn-ghost btn-icon"
            onClick={onSignOut}
            title="Switch workspace or sign out"
            aria-label="Sign out or switch workspace"
          >
            <LogOut size={16} aria-hidden="true" />
          </button>
        </div>
      </div>
    </aside>
  );
}
