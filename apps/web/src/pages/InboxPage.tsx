import { useCallback, useEffect, useState } from 'react';
import { Inbox as InboxIcon, PlusCircle } from 'lucide-react';
import { EmptyState } from '../components/EmptyState';
import { ErrorBanner } from '../components/ErrorBanner';
import { PostCard } from '../components/PostCard';
import { useToast } from '../components/Toast';
import { useAuth } from '../lib/auth';
import { extractErrorInfo } from '../lib/format';
import type { NavSection, Post, Target } from '../lib/types';

interface InboxPageProps {
  onOpenSubmitPost: () => void;
  onNavigate: (section: NavSection) => void;
  refreshTrigger: number;
}

export function InboxPage({
  onOpenSubmitPost,
  onNavigate,
  refreshTrigger,
}: InboxPageProps) {
  const { api } = useAuth();
  const { showToast } = useToast();

  const [posts, setPosts] = useState<Post[]>([]);
  const [targets, setTargets] = useState<Target[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<{ message: string; code?: string; requestId?: string } | null>(
    null
  );

  const [platformFilter, setPlatformFilter] = useState('');
  const [targetFilter, setTargetFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [relevanceFilter, setRelevanceFilter] = useState('');
  const [generatingPostId, setGeneratingPostId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [postRows, targetRows] = await Promise.all([
        api.listPosts({
          platform: platformFilter || undefined,
          target_id: targetFilter || undefined,
          status: statusFilter || undefined,
          limit: 50,
        }),
        api.listTargets({ limit: 100 }),
      ]);
      setPosts(postRows);
      setTargets(targetRows);
    } catch (err) {
      setError(extractErrorInfo(err));
    } finally {
      setLoading(false);
    }
  }, [api, platformFilter, targetFilter, statusFilter]);

  useEffect(() => {
    void load();
  }, [load, refreshTrigger]);

  const filteredPosts = posts.filter((post) => {
    if (!relevanceFilter) return true;
    const topScore = post.drafts.reduce<number | null>((acc, d) => {
      if (d.relevance_score === null || d.relevance_score === undefined) return acc;
      return acc === null ? d.relevance_score : Math.max(acc, d.relevance_score);
    }, null);
    if (topScore === null) return relevanceFilter === 'pending';
    if (relevanceFilter === 'high') return topScore >= 0.75;
    if (relevanceFilter === 'medium') return topScore >= 0.5 && topScore < 0.75;
    if (relevanceFilter === 'low') return topScore < 0.5;
    return true;
  });

  async function handleGenerateDrafts(post: Post) {
    setGeneratingPostId(post.id);
    try {
      const generated = await api.generateDraftsForPost(post.id, { variants: 2 });
      if (generated.length === 0) {
        showToast(
          'No drafts were generated (post did not meet your relevance or topic threshold).',
          'warning'
        );
      } else {
        showToast(`Generated ${generated.length} draft option(s).`, 'success');
      }
      await load();
    } catch (err) {
      showToast(extractErrorInfo(err).message, 'error');
    } finally {
      setGeneratingPostId(null);
    }
  }

  return (
    <div className="stack-lg">
      {error && (
        <ErrorBanner
          title="Unable to load post inbox"
          message={error.message}
          code={error.code}
          requestId={error.requestId}
          onRetry={load}
        />
      )}

      <div className="card">
        <div className="row-between">
          <div className="filter-bar">
            <label htmlFor="inbox-platform-filter" className="sr-only">
              Filter by platform
            </label>
            <select
              id="inbox-platform-filter"
              className="select"
              value={platformFilter}
              onChange={(e) => setPlatformFilter(e.target.value)}
            >
              <option value="">All Platforms</option>
              <option value="linkedin">LinkedIn</option>
              <option value="instagram">Instagram</option>
            </select>

            <label htmlFor="inbox-target-filter" className="sr-only">
              Filter by target
            </label>
            <select
              id="inbox-target-filter"
              className="select"
              value={targetFilter}
              onChange={(e) => setTargetFilter(e.target.value)}
            >
              <option value="">All Watchlist Targets</option>
              {targets.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.display_name || t.profile_url}
                </option>
              ))}
            </select>

            <label htmlFor="inbox-status-filter" className="sr-only">
              Filter by post status
            </label>
            <select
              id="inbox-status-filter"
              className="select"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="">All Statuses</option>
              <option value="new">New</option>
              <option value="drafted">Drafted</option>
              <option value="skipped">Skipped</option>
            </select>

            <label htmlFor="inbox-relevance-filter" className="sr-only">
              Filter by relevance
            </label>
            <select
              id="inbox-relevance-filter"
              className="select"
              value={relevanceFilter}
              onChange={(e) => setRelevanceFilter(e.target.value)}
            >
              <option value="">All Relevance</option>
              <option value="high">High match (75%+)</option>
              <option value="medium">Medium match (50–74%)</option>
              <option value="low">Low match (&lt;50%)</option>
              <option value="pending">Relevance pending</option>
            </select>
          </div>

          <button type="button" className="btn btn-primary" onClick={onOpenSubmitPost}>
            <PlusCircle size={16} aria-hidden="true" />
            Submit Post URL
          </button>
        </div>
      </div>

      {loading ? (
        <div className="stack-md">
          <div className="skeleton" style={{ height: 160 }} />
          <div className="skeleton" style={{ height: 160 }} />
        </div>
      ) : error ? null : filteredPosts.length === 0 ? (
        <EmptyState
          title="No new posts yet. Your watchlist is being checked."
          description="Submit a post URL directly or wait for your authorized feeds to deliver new updates."
          icon={<InboxIcon size={22} />}
          actionLabel="Submit Post URL"
          onAction={onOpenSubmitPost}
        />
      ) : (
        <div className="stack-md">
          {filteredPosts.map((post) => (
            <PostCard
              key={post.id}
              post={post}
              generating={generatingPostId === post.id}
              onGenerateDrafts={handleGenerateDrafts}
              onReviewDrafts={() => onNavigate('drafts')}
            />
          ))}
        </div>
      )}
    </div>
  );
}
