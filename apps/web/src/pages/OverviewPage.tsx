import { useCallback, useEffect, useState } from 'react';
import {
  Activity as ActivityIcon,
  BookmarkCheck,
  CheckCircle2,
  Inbox,
  MessageSquareText,
  Plus,
  Send,
} from 'lucide-react';
import { EmptyState } from '../components/EmptyState';
import { ErrorBanner } from '../components/ErrorBanner';
import { MetricCard } from '../components/MetricCard';
import { SourceStatus } from '../components/SourceStatus';
import { useAuth } from '../lib/auth';
import {
  classifyActivityOutcome,
  extractErrorInfo,
  formatActivityLabel,
  formatDateTime,
  formatRelativeTime,
  getActivityMetadata,
} from '../lib/format';
import type { NavSection, OverviewData } from '../lib/types';

interface OverviewPageProps {
  onNavigate: (section: NavSection) => void;
  onOpenSubmitPost: () => void;
  refreshTrigger: number;
}

export function OverviewPage({
  onNavigate,
  onOpenSubmitPost,
  refreshTrigger,
}: OverviewPageProps) {
  const { api } = useAuth();
  const [data, setData] = useState<OverviewData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<{ message: string; code?: string; requestId?: string } | null>(
    null
  );

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getOverview();
      setData(res);
    } catch (err) {
      setError(extractErrorInfo(err));
    } finally {
      setLoading(false);
    }
  }, [api]);

  useEffect(() => {
    void load();
  }, [load, refreshTrigger]);

  return (
    <div className="stack-lg">
      {error && (
        <ErrorBanner
          title="Unable to load overview"
          message={error.message}
          code={error.code}
          requestId={error.requestId}
          onRetry={load}
        />
      )}

      <section aria-label="Workspace metrics" className="metrics-grid">
        <MetricCard
          label="Tracked Profiles"
          value={data?.tracked_profiles ?? 0}
          subtext={
            data
              ? `${data.active_profiles} active · ${data.unsupported_profiles} unsupported/error`
              : undefined
          }
          icon={<BookmarkCheck size={18} />}
          loading={loading}
          onClick={() => onNavigate('watchlist')}
        />
        <MetricCard
          label="New Posts Detected"
          value={data?.new_posts_detected ?? 0}
          subtext="From authorized sources & manual intake"
          icon={<Inbox size={18} />}
          loading={loading}
          onClick={() => onNavigate('inbox')}
        />
        <MetricCard
          label="Drafts Awaiting Review"
          value={data?.drafts_awaiting_review ?? 0}
          subtext="Pending your edit, copy, or skip"
          icon={<MessageSquareText size={18} />}
          loading={loading}
          onClick={() => onNavigate('drafts')}
        />
        <MetricCard
          label="Drafts Approved / Copied"
          value={data?.drafts_approved_or_copied ?? 0}
          subtext="Copied or opened for manual posting"
          icon={<CheckCircle2 size={18} />}
          loading={loading}
          onClick={() => onNavigate('drafts')}
        />
      </section>

      <div className="overview-grid">
        <section className="card" aria-label="Recent activity">
          <div className="section-header">
            <h2 className="section-title">Recent Activity</h2>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => onNavigate('activity')}
            >
              View Full Timeline
            </button>
          </div>

          {loading ? (
            <div className="stack-sm">
              <div className="skeleton" style={{ height: 48 }} />
              <div className="skeleton" style={{ height: 48 }} />
              <div className="skeleton" style={{ height: 48 }} />
            </div>
          ) : !data || data.recent_activity.length === 0 ? (
            <EmptyState
              title="No activity yet"
              description="Add a watchlist target or submit a post URL to generate your first human-reviewed comment drafts."
              icon={<ActivityIcon size={20} />}
              actionLabel="Submit Post URL"
              onAction={onOpenSubmitPost}
            />
          ) : (
            <div className="stack-sm">
              {data.recent_activity.map((item) => {
                const outcome = classifyActivityOutcome(item.event_type);
                const meta = getActivityMetadata(item);
                const detail =
                  typeof meta.reason === 'string'
                    ? meta.reason
                    : typeof meta.error_code === 'string'
                      ? `Error: ${meta.error_code}`
                      : typeof meta.platform === 'string'
                        ? `Platform: ${meta.platform}`
                        : null;

                return (
                  <div
                    key={item.id}
                    className="card-soft row-between"
                    style={{ padding: '12px 14px' }}
                  >
                    <div>
                      <div className="row-wrap" style={{ gap: 8 }}>
                        <strong style={{ fontSize: 14 }}>{formatActivityLabel(item.event_type)}</strong>
                        <SourceStatus
                          status={
                            outcome === 'failed'
                              ? 'failed'
                              : outcome === 'skipped'
                                ? 'skipped'
                                : 'succeeded'
                          }
                        />
                      </div>
                      {detail && (
                        <p className="meta-text" style={{ marginTop: 3 }}>
                          {detail}
                        </p>
                      )}
                    </div>
                    <span className="meta-text">{formatDateTime(item.created_at)}</span>
                  </div>
                );
              })}
            </div>
          )}
        </section>

        <section className="stack-md" aria-label="Monitoring health and quick actions">
          <div className="card stack-md">
            <div className="section-header" style={{ marginBottom: 0 }}>
              <h2 className="section-title">Monitoring Health</h2>
              {data && <SourceStatus status={data.monitoring_health} />}
            </div>

            {loading ? (
              <div className="skeleton" style={{ height: 64 }} />
            ) : (
              <>
                <p className="meta-text">
                  {data?.monitoring_health === 'healthy'
                    ? 'Authorized monitoring targets are polling normally. Manual targets remain ready for direct post URL intake.'
                    : data?.monitoring_health === 'degraded'
                      ? 'One or more targets reported a source error. Check your Watchlist or Activity timeline for exact error details.'
                      : 'No active auto-polling targets are running right now. Add an Authorized Feed or submit posts manually.'}
                </p>
                <div className="card-soft" style={{ padding: '10px 14px' }}>
                  <div className="meta-text">Last source check</div>
                  <strong style={{ fontSize: 14 }}>
                    {formatRelativeTime(data?.last_checked_at)}
                  </strong>
                </div>
              </>
            )}
          </div>

          <div className="card stack-md">
            <h2 className="section-title">Quick Actions</h2>
            <div className="stack-sm">
              <button
                type="button"
                className="btn btn-primary"
                onClick={onOpenSubmitPost}
              >
                <Send size={15} aria-hidden="true" />
                Submit Post URL for Drafts
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => onNavigate('watchlist')}
              >
                <Plus size={15} aria-hidden="true" />
                Manage Watchlist Targets
              </button>
              <button
                type="button"
                className="btn btn-soft"
                onClick={() => onNavigate('drafts')}
              >
                <MessageSquareText size={15} aria-hidden="true" />
                Open Draft Review Queue ({data?.drafts_awaiting_review ?? 0})
              </button>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
