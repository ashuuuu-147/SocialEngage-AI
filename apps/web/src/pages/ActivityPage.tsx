import { useCallback, useEffect, useState } from 'react';
import { Activity as ActivityIcon, RefreshCw } from 'lucide-react';
import { EmptyState } from '../components/EmptyState';
import { ErrorBanner } from '../components/ErrorBanner';
import { SourceStatus } from '../components/SourceStatus';
import { useAuth } from '../lib/auth';
import {
  classifyActivityOutcome,
  extractErrorInfo,
  formatActivityLabel,
  formatDateTime,
  getActivityMetadata,
} from '../lib/format';
import type { ActivityLog, MonitoringJob } from '../lib/types';

export function ActivityPage() {
  const { api } = useAuth();
  const [logs, setLogs] = useState<ActivityLog[]>([]);
  const [jobs, setJobs] = useState<MonitoringJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<{ message: string; code?: string; requestId?: string } | null>(
    null
  );

  const [eventTypeFilter, setEventTypeFilter] = useState('');
  const [outcomeFilter, setOutcomeFilter] = useState<'all' | 'success' | 'skipped' | 'failed'>('all');

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [activityRows, jobRows] = await Promise.all([
        api.listActivity({ event_type: eventTypeFilter || undefined, limit: 80 }),
        api.listMonitoringJobs(30),
      ]);
      setLogs(activityRows);
      setJobs(jobRows);
    } catch (err) {
      setError(extractErrorInfo(err));
    } finally {
      setLoading(false);
    }
  }, [api, eventTypeFilter]);

  useEffect(() => {
    void load();
  }, [load]);

  const filteredLogs = logs.filter((log) => {
    if (outcomeFilter === 'all') return true;
    return classifyActivityOutcome(log.event_type) === outcomeFilter;
  });

  const uniqueEventTypes = Array.from(new Set(logs.map((l) => l.event_type))).sort();

  return (
    <div className="stack-lg">
      {error && (
        <ErrorBanner
          title="Unable to load activity timeline"
          message={error.message}
          code={error.code}
          requestId={error.requestId}
          onRetry={load}
        />
      )}

      <div className="card">
        <div className="row-between">
          <div className="tab-pills" role="group" aria-label="Filter timeline by outcome">
            {(
              [
                { id: 'all', label: 'All Events' },
                { id: 'success', label: 'Succeeded' },
                { id: 'skipped', label: 'Skipped' },
                { id: 'failed', label: 'Failed' },
              ] as const
            ).map((opt) => (
              <button
                key={opt.id}
                type="button"
                className={`tab-pill ${outcomeFilter === opt.id ? 'is-active' : ''}`}
                onClick={() => setOutcomeFilter(opt.id)}
              >
                {opt.label}
              </button>
            ))}
          </div>

          <div className="row-wrap">
            <label htmlFor="activity-event-type" className="sr-only">
              Filter by event type
            </label>
            <select
              id="activity-event-type"
              className="select"
              value={eventTypeFilter}
              onChange={(e) => setEventTypeFilter(e.target.value)}
            >
              <option value="">All Event Types</option>
              {uniqueEventTypes.map((et) => (
                <option key={et} value={et}>
                  {formatActivityLabel(et)}
                </option>
              ))}
            </select>

            <button type="button" className="btn btn-secondary btn-sm" onClick={load}>
              <RefreshCw size={14} aria-hidden="true" />
              Refresh
            </button>
          </div>
        </div>
      </div>

      <section className="card stack-md" aria-label="Activity timeline">
        <h2 className="section-title">Activity Timeline</h2>
        {loading ? (
          <div className="stack-sm">
            <div className="skeleton" style={{ height: 56 }} />
            <div className="skeleton" style={{ height: 56 }} />
            <div className="skeleton" style={{ height: 56 }} />
          </div>
        ) : filteredLogs.length === 0 ? (
          <EmptyState
            title="No matching activity events"
            description="Source checks, draft actions, and skipped posts will appear here with transparent status details."
            icon={<ActivityIcon size={20} />}
          />
        ) : (
          <div className="stack-sm">
            {filteredLogs.map((log) => {
              const outcome = classifyActivityOutcome(log.event_type);
              const meta = getActivityMetadata(log);
              const metaPairs = Object.entries(meta).filter(
                ([, val]) => val !== null && val !== undefined && val !== ''
              );

              return (
                <div
                  key={log.id}
                  className="card-soft"
                  style={{
                    borderColor:
                      outcome === 'failed'
                        ? 'rgba(196, 81, 97, 0.35)'
                        : outcome === 'skipped'
                          ? 'rgba(183, 121, 40, 0.3)'
                          : 'var(--color-border)',
                  }}
                >
                  <div className="row-between">
                    <div className="row-wrap" style={{ gap: 8 }}>
                      <strong style={{ fontSize: 14 }}>{formatActivityLabel(log.event_type)}</strong>
                      <SourceStatus
                        status={
                          outcome === 'failed'
                            ? 'failed'
                            : outcome === 'skipped'
                              ? 'skipped'
                              : 'succeeded'
                        }
                      />
                      {log.entity_type && (
                        <span className="badge badge-neutral">{log.entity_type}</span>
                      )}
                    </div>
                    <span className="meta-text">{formatDateTime(log.created_at)}</span>
                  </div>

                  {metaPairs.length > 0 && (
                    <div className="row-wrap" style={{ marginTop: 8, gap: 12 }}>
                      {metaPairs.map(([k, v]) => (
                        <span key={k} className="meta-text">
                          <strong>{k}:</strong> {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </section>

      <section className="card stack-md" aria-label="Monitoring jobs">
        <div className="section-header" style={{ marginBottom: 0 }}>
          <h2 className="section-title">Monitoring Jobs</h2>
          <span className="meta-text">Recent automated source check runs</span>
        </div>

        {loading ? (
          <div className="skeleton" style={{ height: 120 }} />
        ) : jobs.length === 0 ? (
          <p className="meta-text">No background monitoring jobs have run yet.</p>
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Target ID</th>
                  <th>Status</th>
                  <th>Items Found</th>
                  <th>Run Time</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <tr key={job.id}>
                    <td>
                      <code>{job.target_id.slice(0, 8)}...</code>
                    </td>
                    <td>
                      <SourceStatus status={job.status} />
                    </td>
                    <td>{job.items_found}</td>
                    <td>{formatDateTime(job.finished_at || job.started_at || job.created_at)}</td>
                    <td>
                      {job.error_code || job.error_summary ? (
                        <span style={{ color: 'var(--color-danger-text)' }}>
                          {job.error_code ? `${job.error_code}: ` : ''}
                          {job.error_summary || 'Source check failed.'}
                        </span>
                      ) : (
                        <span className="meta-text">Completed cleanly</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
