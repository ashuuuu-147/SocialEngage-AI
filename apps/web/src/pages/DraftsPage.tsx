import { useCallback, useEffect, useState } from 'react';
import { ExternalLink, MessageSquareText, ShieldCheck } from 'lucide-react';
import { DraftEditor } from '../components/DraftEditor';
import { EmptyState } from '../components/EmptyState';
import { ErrorBanner } from '../components/ErrorBanner';
import { PlatformBadge } from '../components/PlatformBadge';
import { useToast } from '../components/Toast';
import { useAuth } from '../lib/auth';
import { extractErrorInfo, formatDateTime } from '../lib/format';
import type { DraftAction, DraftWithPost } from '../lib/types';

interface DraftsPageProps {
  onOpenSubmitPost: () => void;
  onDraftsChanged: () => void;
  refreshTrigger: number;
}

const STATUS_FILTERS = [
  { value: '', label: 'All' },
  { value: 'pending', label: 'Pending' },
  { value: 'edited', label: 'Edited' },
  { value: 'copied', label: 'Copied' },
  { value: 'opened', label: 'Opened' },
  { value: 'skipped', label: 'Skipped' },
  { value: 'archived', label: 'Archived' },
];

export function DraftsPage({
  onOpenSubmitPost,
  onDraftsChanged,
  refreshTrigger,
}: DraftsPageProps) {
  const { api } = useAuth();
  const { showToast } = useToast();

  const [drafts, setDrafts] = useState<DraftWithPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<{ message: string; code?: string; requestId?: string } | null>(
    null
  );
  const [statusFilter, setStatusFilter] = useState('');
  const [platformFilter, setPlatformFilter] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const rows = await api.listDrafts({
        status: statusFilter || undefined,
        platform: platformFilter || undefined,
        limit: 50,
      });
      setDrafts(rows);
    } catch (err) {
      setError(extractErrorInfo(err));
    } finally {
      setLoading(false);
    }
  }, [api, statusFilter, platformFilter]);

  useEffect(() => {
    void load();
  }, [load, refreshTrigger]);

  async function handleSaveEdit(draftId: string, editedText: string) {
    try {
      const updated = await api.updateDraft(draftId, { edited_text: editedText });
      setDrafts((prev) =>
        prev.map((d) => (d.id === draftId ? { ...d, ...updated } : d))
      );
      onDraftsChanged();
      showToast('Draft edits saved.', 'success');
    } catch (err) {
      showToast(extractErrorInfo(err).message, 'error');
      throw err;
    }
  }

  async function handleRegenerate(
    draftId: string,
    params: { tone: string; length: 'short' | 'medium' | 'detailed'; instruction?: string }
  ) {
    try {
      const updated = await api.regenerateDraft(draftId, params);
      setDrafts((prev) =>
        prev.map((d) => (d.id === draftId ? { ...d, ...updated } : d))
      );
      onDraftsChanged();
      showToast('Generated a fresh comment draft.', 'success');
    } catch (err) {
      showToast(extractErrorInfo(err).message, 'error');
      throw err;
    }
  }

  async function handleMark(draftId: string, action: DraftAction) {
    try {
      const updated = await api.markDraft(draftId, action);
      setDrafts((prev) =>
        prev.map((d) => (d.id === draftId ? { ...d, ...updated } : d))
      );
      onDraftsChanged();
      if (action !== 'copied') {
        showToast(`Draft marked as ${action}.`, 'info');
      }
    } catch (err) {
      showToast(extractErrorInfo(err).message, 'error');
      throw err;
    }
  }

  async function handleDelete(draftId: string) {
    try {
      await api.deleteDraft(draftId);
      setDrafts((prev) => prev.filter((d) => d.id !== draftId));
      onDraftsChanged();
      showToast('Draft deleted.', 'info');
    } catch (err) {
      showToast(extractErrorInfo(err).message, 'error');
      throw err;
    }
  }

  return (
    <div className="stack-lg">
      <div className="info-banner">
        <ShieldCheck size={18} style={{ flexShrink: 0, marginTop: 2 }} aria-hidden="true" />
        <div style={{ fontSize: 13 }}>
          <strong>Review Before Posting:</strong> Edit any draft, copy it to your clipboard, and
          open the original post to paste and publish yourself. SocialEngage AI never posts on your
          behalf.
        </div>
      </div>

      {error && (
        <ErrorBanner
          title="Unable to load draft queue"
          message={error.message}
          code={error.code}
          requestId={error.requestId}
          onRetry={load}
        />
      )}

      <div className="card">
        <div className="row-between">
          <div className="tab-pills" role="group" aria-label="Filter drafts by status">
            {STATUS_FILTERS.map((sf) => (
              <button
                key={sf.value || 'all'}
                type="button"
                className={`tab-pill ${statusFilter === sf.value ? 'is-active' : ''}`}
                onClick={() => setStatusFilter(sf.value)}
              >
                {sf.label}
              </button>
            ))}
          </div>

          <div className="filter-bar">
            <label htmlFor="drafts-platform-filter" className="sr-only">
              Filter drafts by platform
            </label>
            <select
              id="drafts-platform-filter"
              className="select"
              value={platformFilter}
              onChange={(e) => setPlatformFilter(e.target.value)}
            >
              <option value="">All Platforms</option>
              <option value="linkedin">LinkedIn</option>
              <option value="instagram">Instagram</option>
            </select>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="stack-md">
          <div className="skeleton" style={{ height: 260 }} />
          <div className="skeleton" style={{ height: 260 }} />
        </div>
      ) : error ? null : drafts.length === 0 ? (
        <EmptyState
          title="No drafts match this view"
          description="Submit a post URL or clear your status filters to review comment suggestions."
          icon={<MessageSquareText size={22} />}
          actionLabel="Submit Post URL"
          onAction={onOpenSubmitPost}
        />
      ) : (
        <div className="stack-lg">
          {drafts.map((draft) => {
            const post = draft.post;
            return (
              <article key={draft.id} className="card draft-review-pair">
                <div className="stack-md">
                  <div className="row-between">
                    <div className="row-wrap" style={{ gap: 8 }}>
                      <strong style={{ fontSize: 15 }}>
                        {post?.author_name || 'Original Post'}
                      </strong>
                      {post && <PlatformBadge platform={post.platform} />}
                    </div>
                    <span className="meta-text">{formatDateTime(draft.created_at)}</span>
                  </div>

                  {post?.content_text ? (
                    <p className="post-preview-text">{post.content_text}</p>
                  ) : (
                    <p className="meta-text">Post preview unavailable.</p>
                  )}

                  {post?.canonical_url && (
                    <div>
                      <a
                        href={post.canonical_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn btn-secondary btn-sm"
                      >
                        <ExternalLink size={14} aria-hidden="true" />
                        View Original Post
                      </a>
                    </div>
                  )}
                </div>

                <DraftEditor
                  draft={draft}
                  onSaveEdit={handleSaveEdit}
                  onRegenerate={handleRegenerate}
                  onMark={handleMark}
                  onDelete={handleDelete}
                  onCopiedSuccess={() =>
                    showToast('Comment copied to clipboard!', 'success')
                  }
                />
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}
