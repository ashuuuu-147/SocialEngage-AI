import { ExternalLink, MessageSquarePlus, Sparkles } from 'lucide-react';
import { formatDateTime, getInitials } from '../lib/format';
import type { Post } from '../lib/types';
import { PlatformBadge } from './PlatformBadge';
import { RelevanceBadge } from './RelevanceBadge';

interface PostCardProps {
  post: Post;
  generating?: boolean;
  onGenerateDrafts: (post: Post) => void;
  onReviewDrafts: (post: Post) => void;
}

export function PostCard({
  post,
  generating = false,
  onGenerateDrafts,
  onReviewDrafts,
}: PostCardProps) {
  const author = post.author_name || 'Unknown Creator';
  const topRelevance = post.drafts.reduce<number | null>((acc, d) => {
    if (d.relevance_score === null || d.relevance_score === undefined) return acc;
    return acc === null ? d.relevance_score : Math.max(acc, d.relevance_score);
  }, null);

  const pendingCount = post.drafts.filter(
    (d) => d.status === 'pending' || d.status === 'edited'
  ).length;

  return (
    <article className="card post-card" aria-label={`Post by ${author}`}>
      <div className="row-between">
        <div className="row-wrap">
          <div className="avatar-placeholder" style={{ width: 36, height: 36, fontSize: 12 }} aria-hidden="true">
            {getInitials(author)}
          </div>
          <div>
            <div className="row-wrap" style={{ gap: 8 }}>
              <strong style={{ fontSize: 15 }}>{author}</strong>
              <PlatformBadge platform={post.platform} />
              <RelevanceBadge score={topRelevance} />
            </div>
            <div className="meta-text" style={{ marginTop: 2 }}>
              Posted: {post.published_at ? formatDateTime(post.published_at) : 'Not specified'} · Detected:{' '}
              {formatDateTime(post.detected_at)}
            </div>
          </div>
        </div>

        <span className="badge badge-neutral">
          {post.drafts.length} {post.drafts.length === 1 ? 'draft' : 'drafts'}
          {pendingCount > 0 ? ` (${pendingCount} awaiting review)` : ''}
        </span>
      </div>

      {post.content_text ? (
        <p className="post-preview-text">{post.content_text}</p>
      ) : (
        <p className="meta-text" style={{ fontStyle: 'italic' }}>
          No text preview stored for this post yet.
        </p>
      )}

      <div className="row-between">
        <a
          href={post.canonical_url}
          target="_blank"
          rel="noopener noreferrer"
          className="btn btn-secondary btn-sm"
        >
          <ExternalLink size={14} aria-hidden="true" />
          Open Original Post
        </a>

        <div className="row-wrap" style={{ gap: 8 }}>
          <button
            type="button"
            className="btn btn-soft btn-sm"
            onClick={() => onGenerateDrafts(post)}
            disabled={generating || !post.content_text}
            title={!post.content_text ? 'Post preview text is required to generate drafts' : undefined}
          >
            <Sparkles size={14} aria-hidden="true" />
            {generating ? 'Generating...' : post.drafts.length > 0 ? 'Generate More Drafts' : 'Generate Drafts'}
          </button>

          {post.drafts.length > 0 && (
            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={() => onReviewDrafts(post)}
            >
              <MessageSquarePlus size={14} aria-hidden="true" />
              Review Drafts
            </button>
          )}
        </div>
      </div>
    </article>
  );
}
