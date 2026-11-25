import React, { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import { extractErrorInfo } from '../lib/format';
import type { PlatformType, Post, Target } from '../lib/types';
import { ErrorBanner } from './ErrorBanner';

interface ManualPostModalProps {
  open: boolean;
  targets: Target[];
  initialTargetId?: string;
  onClose: () => void;
  onSubmitManual: (payload: {
    platform: PlatformType;
    post_url: string;
    target_id?: string;
    author_name?: string;
    content_text?: string;
    media_type?: string;
    auto_generate_drafts: boolean;
  }) => Promise<Post>;
  onSuccess: (post: Post) => void;
}

export function ManualPostModal({
  open,
  targets,
  initialTargetId,
  onClose,
  onSubmitManual,
  onSuccess,
}: ManualPostModalProps) {
  const [platform, setPlatform] = useState<PlatformType>('linkedin');
  const [targetId, setTargetId] = useState(initialTargetId || '');
  const [postUrl, setPostUrl] = useState('');
  const [authorName, setAuthorName] = useState('');
  const [contentText, setContentText] = useState('');
  const [mediaType, setMediaType] = useState('text');
  const [autoGenerate, setAutoGenerate] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<{ message: string; code?: string; requestId?: string } | null>(
    null
  );

  useEffect(() => {
    if (!open) return;
    setError(null);
    if (initialTargetId) {
      setTargetId(initialTargetId);
      const found = targets.find((t) => t.id === initialTargetId);
      if (found) {
        setPlatform(found.platform);
        setAuthorName(found.display_name || '');
      }
    }
  }, [open, initialTargetId, targets]);

  useEffect(() => {
    if (!open) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !submitting) onClose();
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [open, submitting, onClose]);

  if (!open) return null;

  const filteredTargets = targets.filter((t) => t.platform === platform);

  function handleTargetChange(nextId: string) {
    setTargetId(nextId);
    const matched = targets.find((t) => t.id === nextId);
    if (matched) {
      setPlatform(matched.platform);
      if (!authorName) {
        setAuthorName(matched.display_name || '');
      }
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const created = await onSubmitManual({
        platform,
        post_url: postUrl.trim(),
        target_id: targetId || undefined,
        author_name: authorName.trim() || undefined,
        content_text: contentText.trim() || undefined,
        media_type: mediaType,
        auto_generate_drafts: autoGenerate,
      });
      setPostUrl('');
      setAuthorName('');
      setContentText('');
      onSuccess(created);
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
        aria-labelledby="manual-post-modal-title"
      >
        <div className="row-between">
          <div>
            <h2 id="manual-post-modal-title" className="section-title">
              Submit Post URL & Text
            </h2>
            <p className="meta-text">
              Directly ingest a LinkedIn or Instagram post URL and preview text to generate human-reviewed drafts.
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
            title="Could not ingest post"
            message={error.message}
            code={error.code}
            requestId={error.requestId}
          />
        )}

        <form className="stack-md" onSubmit={handleSubmit}>
          <div className="cards-grid-2" style={{ gap: 12 }}>
            <div className="field">
              <label htmlFor="intake-platform" className="field-label">
                Platform
              </label>
              <select
                id="intake-platform"
                className="select"
                value={platform}
                onChange={(e) => {
                  const nextPlatform = e.target.value as PlatformType;
                  setPlatform(nextPlatform);
                  setTargetId('');
                }}
              >
                <option value="linkedin">LinkedIn</option>
                <option value="instagram">Instagram</option>
              </select>
            </div>

            <div className="field">
              <label htmlFor="intake-target" className="field-label">
                Watchlist Target (optional)
              </label>
              <select
                id="intake-target"
                className="select"
                value={targetId}
                onChange={(e) => handleTargetChange(e.target.value)}
              >
                <option value="">None (standalone post)</option>
                {filteredTargets.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.display_name || t.profile_url}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="field">
            <label htmlFor="intake-post-url" className="field-label">
              Post URL
            </label>
            <input
              id="intake-post-url"
              type="url"
              className="input"
              required
              placeholder={
                platform === 'linkedin'
                  ? 'https://www.linkedin.com/feed/update/urn:li:activity:...'
                  : 'https://www.instagram.com/p/...'
              }
              value={postUrl}
              onChange={(e) => setPostUrl(e.target.value)}
            />
          </div>

          <div className="cards-grid-2" style={{ gap: 12 }}>
            <div className="field">
              <label htmlFor="intake-author" className="field-label">
                Author Name (optional)
              </label>
              <input
                id="intake-author"
                type="text"
                className="input"
                placeholder="e.g., Maya Lin"
                value={authorName}
                onChange={(e) => setAuthorName(e.target.value)}
                maxLength={160}
              />
            </div>

            <div className="field">
              <label htmlFor="intake-media-type" className="field-label">
                Post Format
              </label>
              <select
                id="intake-media-type"
                className="select"
                value={mediaType}
                onChange={(e) => setMediaType(e.target.value)}
              >
                <option value="text">Text / Article</option>
                <option value="image">Image</option>
                <option value="carousel">Carousel</option>
                <option value="video">Video / Reel</option>
              </select>
            </div>
          </div>

          <div className="field">
            <label htmlFor="intake-content" className="field-label">
              Post Text / Caption Preview
            </label>
            <textarea
              id="intake-content"
              className="textarea"
              placeholder="Paste the post text or caption here so the AI can draft context-specific comment options..."
              value={contentText}
              onChange={(e) => setContentText(e.target.value)}
              maxLength={10000}
              rows={4}
            />
            <span className="field-hint">
              Draft generation runs only when preview text is provided. No content is ever auto-posted.
            </span>
          </div>

          <label className="row-wrap" style={{ gap: 8, cursor: 'pointer', fontSize: 14 }}>
            <input
              type="checkbox"
              checked={autoGenerate}
              onChange={(e) => setAutoGenerate(e.target.checked)}
            />
            <span>Automatically generate 2 comment draft options after saving</span>
          </label>

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
              {submitting ? 'Submitting...' : 'Submit Post'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
