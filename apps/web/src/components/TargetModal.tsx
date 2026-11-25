import React, { useEffect, useState } from 'react';
import { Info, X } from 'lucide-react';
import { extractErrorInfo } from '../lib/format';
import type {
  PlatformType,
  SourceCapability,
  SourceType,
  Target,
  TargetCreateRequest,
  TargetUpdateRequest,
} from '../lib/types';
import { ErrorBanner } from './ErrorBanner';

interface TargetModalProps {
  open: boolean;
  editingTarget: Target | null;
  capabilities: SourceCapability[];
  onClose: () => void;
  onCreate: (payload: TargetCreateRequest) => Promise<Target>;
  onUpdate: (targetId: string, payload: TargetUpdateRequest) => Promise<Target>;
}

const SOURCE_OPTIONS: Array<{ value: SourceType; label: string }> = [
  { value: 'manual', label: 'Manual Post Intake (Always Available)' },
  { value: 'authorized_feed', label: 'Authorized RSS / Atom Feed' },
  { value: 'notification_import', label: 'Notification Import' },
  { value: 'official_api', label: 'Official Platform API (Restricted)' },
];

export function TargetModal({
  open,
  editingTarget,
  capabilities,
  onClose,
  onCreate,
  onUpdate,
}: TargetModalProps) {
  const [platform, setPlatform] = useState<PlatformType>('linkedin');
  const [profileUrl, setProfileUrl] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [sourceType, setSourceType] = useState<SourceType>('manual');
  const [feedUrl, setFeedUrl] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<{ message: string; code?: string; requestId?: string } | null>(
    null
  );

  useEffect(() => {
    if (!open) return;
    setError(null);
    if (editingTarget) {
      setPlatform(editingTarget.platform);
      setProfileUrl(editingTarget.profile_url);
      setDisplayName(editingTarget.display_name || '');
      setSourceType(editingTarget.source_type);
      setFeedUrl(
        typeof editingTarget.preferences?.feed_url === 'string'
          ? editingTarget.preferences.feed_url
          : ''
      );
    } else {
      setPlatform('linkedin');
      setProfileUrl('');
      setDisplayName('');
      setSourceType('manual');
      setFeedUrl('');
    }
  }, [open, editingTarget]);

  useEffect(() => {
    if (!open) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !submitting) onClose();
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [open, submitting, onClose]);

  if (!open) return null;

  const currentCap = capabilities.find(
    (c) => c.platform === platform && c.source_type === sourceType
  );

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const preferences: Record<string, unknown> = editingTarget
        ? { ...editingTarget.preferences }
        : {};
      if (sourceType === 'authorized_feed' && feedUrl.trim()) {
        preferences.feed_url = feedUrl.trim();
      } else if (sourceType !== 'authorized_feed') {
        delete preferences.feed_url;
      }

      if (editingTarget) {
        await onUpdate(editingTarget.id, {
          display_name: displayName.trim() || undefined,
          source_type: sourceType,
          preferences,
        });
      } else {
        await onCreate({
          platform,
          profile_url: profileUrl.trim(),
          display_name: displayName.trim() || undefined,
          source_type: sourceType,
          preferences,
        });
      }
      onClose();
    } catch (err) {
      setError(extractErrorInfo(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      className="modal-overlay"
      role="presentation"
      onClick={(e) => {
        if (e.target === e.currentTarget && !submitting) onClose();
      }}
    >
      <div
        className="modal-card"
        role="dialog"
        aria-modal="true"
        aria-labelledby="target-modal-title"
      >
        <div className="row-between">
          <div>
            <h2 id="target-modal-title" className="section-title">
              {editingTarget ? 'Edit Watchlist Target' : 'Add Watchlist Target'}
            </h2>
            <p className="meta-text">
              Track creators or company pages using compliant, user-authorized methods.
            </p>
          </div>
          <button
            type="button"
            className="btn btn-ghost btn-icon"
            onClick={onClose}
            disabled={submitting}
            aria-label="Close modal"
          >
            <X size={18} aria-hidden="true" />
          </button>
        </div>

        {error && (
          <ErrorBanner
            title="Could not save watchlist target"
            message={error.message}
            code={error.code}
            requestId={error.requestId}
          />
        )}

        <form className="stack-md" onSubmit={handleSubmit}>
          <div className="cards-grid-2" style={{ gap: 12 }}>
            <div className="field">
              <label htmlFor="target-platform" className="field-label">
                Platform
              </label>
              <select
                id="target-platform"
                className="select"
                value={platform}
                disabled={Boolean(editingTarget)}
                onChange={(e) => setPlatform(e.target.value as PlatformType)}
              >
                <option value="linkedin">LinkedIn</option>
                <option value="instagram">Instagram</option>
              </select>
            </div>

            <div className="field">
              <label htmlFor="target-source-type" className="field-label">
                Source Method
              </label>
              <select
                id="target-source-type"
                className="select"
                value={sourceType}
                onChange={(e) => setSourceType(e.target.value as SourceType)}
              >
                {SOURCE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {currentCap && (
            <div
              className="info-banner"
              style={
                currentCap.supported
                  ? undefined
                  : {
                      background: 'var(--color-warning-soft)',
                      color: 'var(--color-warning-text)',
                      borderColor: 'rgba(183, 121, 40, 0.35)',
                    }
              }
            >
              <Info size={18} style={{ flexShrink: 0, marginTop: 2 }} aria-hidden="true" />
              <div style={{ fontSize: 13 }}>
                <strong>{currentCap.supported ? 'Supported source' : 'Source currently unsupported'}:</strong>{' '}
                {currentCap.reason} {currentCap.documentation_note}
              </div>
            </div>
          )}

          <div className="field">
            <label htmlFor="target-profile-url" className="field-label">
              Profile or Page URL
            </label>
            <input
              id="target-profile-url"
              type="url"
              className="input"
              required
              disabled={Boolean(editingTarget)}
              placeholder={
                platform === 'linkedin'
                  ? 'https://www.linkedin.com/in/creator-handle'
                  : 'https://www.instagram.com/creator_handle/'
              }
              value={profileUrl}
              onChange={(e) => setProfileUrl(e.target.value)}
            />
          </div>

          <div className="field">
            <label htmlFor="target-display-name" className="field-label">
              Display Name
            </label>
            <input
              id="target-display-name"
              type="text"
              className="input"
              placeholder="e.g., Maya Lin (Product Ops)"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              maxLength={160}
            />
          </div>

          {sourceType === 'authorized_feed' && (
            <div className="field">
              <label htmlFor="target-feed-url" className="field-label">
                Authorized RSS / Atom Feed URL
              </label>
              <input
                id="target-feed-url"
                type="url"
                className="input"
                placeholder="https://example.com/creator/feed.xml"
                value={feedUrl}
                onChange={(e) => setFeedUrl(e.target.value)}
              />
              <span className="field-hint">
                Stored in target preferences. Only public HTTP(S) feed URLs you provide are fetched.
              </span>
            </div>
          )}

          <div className="row-wrap" style={{ justifyContent: 'flex-end', marginTop: 6 }}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onClose}
              disabled={submitting}
            >
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? 'Saving...' : editingTarget ? 'Save Changes' : 'Add Target'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
