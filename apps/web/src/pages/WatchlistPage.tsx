import { useCallback, useEffect, useState } from 'react';
import { BookmarkCheck, Info, Plus, Search } from 'lucide-react';
import { ConfirmDialog } from '../components/ConfirmDialog';
import { EmptyState } from '../components/EmptyState';
import { ErrorBanner } from '../components/ErrorBanner';
import { ProfileRow } from '../components/ProfileRow';
import { TargetModal } from '../components/TargetModal';
import { useToast } from '../components/Toast';
import { useAuth } from '../lib/auth';
import { extractErrorInfo } from '../lib/format';
import type {
  SourceCapability,
  Target,
  TargetCreateRequest,
  TargetUpdateRequest,
} from '../lib/types';

interface WatchlistPageProps {
  onOpenSubmitPostForTarget: (targetId: string) => void;
  onTargetsChanged: () => void;
}

export function WatchlistPage({
  onOpenSubmitPostForTarget,
  onTargetsChanged,
}: WatchlistPageProps) {
  const { api } = useAuth();
  const { showToast } = useToast();

  const [targets, setTargets] = useState<Target[]>([]);
  const [capabilities, setCapabilities] = useState<SourceCapability[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<{ message: string; code?: string; requestId?: string } | null>(
    null
  );

  const [search, setSearch] = useState('');
  const [platformFilter, setPlatformFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  const [modalOpen, setModalOpen] = useState(false);
  const [editingTarget, setEditingTarget] = useState<Target | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [targetToDelete, setTargetToDelete] = useState<Target | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [rows, caps] = await Promise.all([
        api.listTargets({
          platform: platformFilter || undefined,
          status: statusFilter || undefined,
          limit: 100,
        }),
        api.getSourceCapabilities(),
      ]);
      setTargets(rows);
      setCapabilities(caps);
    } catch (err) {
      setError(extractErrorInfo(err));
    } finally {
      setLoading(false);
    }
  }, [api, platformFilter, statusFilter]);

  useEffect(() => {
    void load();
  }, [load]);

  const filteredTargets = targets.filter((t) => {
    if (!search.trim()) return true;
    const q = search.trim().toLowerCase();
    return (
      (t.display_name || '').toLowerCase().includes(q) ||
      t.profile_url.toLowerCase().includes(q)
    );
  });

  async function handleCreate(payload: TargetCreateRequest) {
    const created = await api.createTarget(payload);
    setTargets((prev) => [created, ...prev]);
    onTargetsChanged();
    showToast(`Added ${created.display_name || created.profile_url} to watchlist.`, 'success');
    return created;
  }

  async function handleUpdate(targetId: string, payload: TargetUpdateRequest) {
    const updated = await api.updateTarget(targetId, payload);
    setTargets((prev) => prev.map((t) => (t.id === targetId ? updated : t)));
    onTargetsChanged();
    showToast('Watchlist target updated.', 'success');
    return updated;
  }

  async function handleTogglePause(target: Target) {
    setBusyId(target.id);
    try {
      const nextStatus = target.status === 'paused' ? 'active' : 'paused';
      const updated = await api.updateTarget(target.id, { status: nextStatus });
      setTargets((prev) => prev.map((t) => (t.id === target.id ? updated : t)));
      onTargetsChanged();
      showToast(
        nextStatus === 'paused' ? 'Target monitoring paused.' : 'Target monitoring resumed.',
        'info'
      );
    } catch (err) {
      showToast(extractErrorInfo(err).message, 'error');
    } finally {
      setBusyId(null);
    }
  }

  async function handleCheckNow(target: Target) {
    if (target.source_type === 'manual') {
      onOpenSubmitPostForTarget(target.id);
      return;
    }
    setBusyId(target.id);
    try {
      const res = await api.checkTarget(target.id);
      if (res.status === 'manual_only') {
        showToast(res.message || 'Use Manual Intake to submit posts.', 'info');
      } else {
        showToast('Monitoring check completed.', 'success');
        await load();
      }
      onTargetsChanged();
    } catch (err) {
      showToast(extractErrorInfo(err).message, 'error');
    } finally {
      setBusyId(null);
    }
  }

  async function handleConfirmDelete() {
    if (!targetToDelete) return;
    setBusyId(targetToDelete.id);
    try {
      await api.deleteTarget(targetToDelete.id);
      setTargets((prev) => prev.filter((t) => t.id !== targetToDelete.id));
      onTargetsChanged();
      showToast('Target removed from watchlist.', 'info');
      setTargetToDelete(null);
    } catch (err) {
      showToast(extractErrorInfo(err).message, 'error');
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="stack-lg">
      <div className="info-banner">
        <Info size={18} style={{ flexShrink: 0, marginTop: 2 }} aria-hidden="true" />
        <div style={{ fontSize: 13 }}>
          <strong>Compliant Source Availability:</strong> LinkedIn and Instagram restrict automated
          third-party profile scraping. Targets using <strong>Official API</strong> without partner
          credentials are clearly marked <strong>Unsupported Source</strong>. Use{' '}
          <strong>Manual Intake</strong>, <strong>Authorized Feed</strong> (with your RSS/Atom URL),
          or <strong>Notification Import</strong> for reliable updates.
        </div>
      </div>

      {error && (
        <ErrorBanner
          title="Unable to load watchlist"
          message={error.message}
          code={error.code}
          requestId={error.requestId}
          onRetry={load}
        />
      )}

      <div className="card">
        <div className="row-between">
          <div className="filter-bar" style={{ flex: 1 }}>
            <div className="filter-search" style={{ position: 'relative' }}>
              <label htmlFor="watchlist-search" className="sr-only">
                Search watchlist targets
              </label>
              <Search
                size={15}
                aria-hidden="true"
                style={{
                  position: 'absolute',
                  left: 12,
                  top: '50%',
                  transform: 'translateY(-50%)',
                  color: 'var(--color-text-muted)',
                }}
              />
              <input
                id="watchlist-search"
                type="search"
                className="input"
                style={{ paddingLeft: 34, width: '100%' }}
                placeholder="Search by name or URL..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>

            <label htmlFor="watchlist-platform-filter" className="sr-only">
              Filter by platform
            </label>
            <select
              id="watchlist-platform-filter"
              className="select"
              value={platformFilter}
              onChange={(e) => setPlatformFilter(e.target.value)}
            >
              <option value="">All Platforms</option>
              <option value="linkedin">LinkedIn</option>
              <option value="instagram">Instagram</option>
            </select>

            <label htmlFor="watchlist-status-filter" className="sr-only">
              Filter by status
            </label>
            <select
              id="watchlist-status-filter"
              className="select"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="">All Statuses</option>
              <option value="active">Active</option>
              <option value="paused">Paused</option>
              <option value="unsupported">Unsupported</option>
              <option value="error">Error</option>
            </select>
          </div>

          <button
            type="button"
            className="btn btn-primary"
            onClick={() => {
              setEditingTarget(null);
              setModalOpen(true);
            }}
          >
            <Plus size={16} aria-hidden="true" />
            Add Target
          </button>
        </div>
      </div>

      {loading ? (
        <div className="stack-md">
          <div className="skeleton" style={{ height: 96 }} />
          <div className="skeleton" style={{ height: 96 }} />
        </div>
      ) : filteredTargets.length === 0 ? (
        <EmptyState
          title="No watchlist targets match your filters"
          description="Add a LinkedIn or Instagram creator profile to organize your engagement workflow."
          icon={<BookmarkCheck size={22} />}
          actionLabel="Add Watchlist Target"
          onAction={() => {
            setEditingTarget(null);
            setModalOpen(true);
          }}
        />
      ) : (
        <div className="stack-md">
          {filteredTargets.map((target) => (
            <ProfileRow
              key={target.id}
              target={target}
              busy={busyId === target.id}
              onTogglePause={handleTogglePause}
              onCheckNow={handleCheckNow}
              onEdit={(t) => {
                setEditingTarget(t);
                setModalOpen(true);
              }}
              onRemove={(t) => setTargetToDelete(t)}
            />
          ))}
        </div>
      )}

      <TargetModal
        open={modalOpen}
        editingTarget={editingTarget}
        capabilities={capabilities}
        onClose={() => setModalOpen(false)}
        onCreate={handleCreate}
        onUpdate={handleUpdate}
      />

      <ConfirmDialog
        open={Boolean(targetToDelete)}
        title="Remove watchlist target?"
        description={`Remove "${targetToDelete?.display_name || targetToDelete?.profile_url}" from your watchlist? Previously ingested posts and drafts will remain intact.`}
        confirmLabel="Remove Target"
        busy={busyId !== null && busyId === targetToDelete?.id}
        onConfirm={handleConfirmDelete}
        onCancel={() => setTargetToDelete(null)}
      />
    </div>
  );
}
