import { Edit3, ExternalLink, Pause, Play, RefreshCw, Trash2 } from 'lucide-react';
import { formatRelativeTime, formatSourceTypeLabel, getInitials } from '../lib/format';
import type { Target } from '../lib/types';
import { PlatformBadge } from './PlatformBadge';
import { SourceStatus } from './SourceStatus';

interface ProfileRowProps {
  target: Target;
  busy?: boolean;
  onTogglePause: (target: Target) => void;
  onCheckNow: (target: Target) => void;
  onEdit: (target: Target) => void;
  onRemove: (target: Target) => void;
}

export function ProfileRow({
  target,
  busy = false,
  onTogglePause,
  onCheckNow,
  onEdit,
  onRemove,
}: ProfileRowProps) {
  const displayName = target.display_name || target.profile_url;
  const isPaused = target.status === 'paused';

  return (
    <article className="card profile-row" aria-label={`Watchlist target ${displayName}`}>
      <div className="profile-row-main">
        <div className="avatar-placeholder" aria-hidden="true">
          {getInitials(displayName)}
        </div>
        <div className="profile-row-info">
          <div className="profile-row-title">
            <h3 className="profile-name">{displayName}</h3>
            <PlatformBadge platform={target.platform} />
            <SourceStatus status={target.status} />
            <span className="badge badge-neutral">{formatSourceTypeLabel(target.source_type)}</span>
          </div>
          <a
            href={target.profile_url}
            target="_blank"
            rel="noopener noreferrer"
            className="profile-url"
          >
            {target.profile_url}{' '}
            <ExternalLink size={12} style={{ verticalAlign: 'middle' }} aria-hidden="true" />
          </a>
          <div className="profile-meta">
            <span>Last checked: {formatRelativeTime(target.last_checked_at)}</span>
            {target.last_error_code && (
              <span style={{ color: 'var(--color-danger-text)', fontWeight: 600 }}>
                Error: {target.last_error_code}
              </span>
            )}
          </div>
          {target.capability && !target.capability.supported && (
            <p className="field-hint" style={{ marginTop: 6, color: 'var(--color-warning-text)' }}>
              {target.capability.reason} {target.capability.documentation_note}
            </p>
          )}
        </div>
      </div>

      <div className="profile-actions">
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={() => onCheckNow(target)}
          disabled={busy}
        >
          <RefreshCw size={14} aria-hidden="true" />
          {target.source_type === 'manual' ? 'Manual Intake' : 'Check Now'}
        </button>

        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={() => onTogglePause(target)}
          disabled={busy || target.status === 'unsupported'}
          title={
            target.status === 'unsupported'
              ? 'Switch source method to Manual or Authorized Feed to activate'
              : undefined
          }
        >
          {isPaused ? <Play size={14} aria-hidden="true" /> : <Pause size={14} aria-hidden="true" />}
          {isPaused ? 'Resume' : 'Pause'}
        </button>

        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={() => onEdit(target)}
          disabled={busy}
          aria-label={`Edit ${displayName}`}
        >
          <Edit3 size={14} aria-hidden="true" />
          Edit
        </button>

        <button
          type="button"
          className="btn btn-danger-soft btn-sm"
          onClick={() => onRemove(target)}
          disabled={busy}
          aria-label={`Remove ${displayName}`}
        >
          <Trash2 size={14} aria-hidden="true" />
          Remove
        </button>
      </div>
    </article>
  );
}
