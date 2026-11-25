import { ApiError } from './api';
import type { ActivityLog, SourceType } from './types';

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return 'Never';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return 'Unknown';
  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function formatRelativeTime(iso: string | null | undefined): string {
  if (!iso) return 'Not yet checked';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return 'Unknown';
  const diffMs = Date.now() - date.getTime();
  const diffMin = Math.round(diffMs / 60_000);
  if (diffMin < 1) return 'Just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.round(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.round(diffHr / 24);
  return `${diffDay}d ago`;
}

export function getInitials(name: string | null | undefined): string {
  const clean = (name || '').trim();
  if (!clean) return 'SE';
  const parts = clean.split(/\s+/).filter(Boolean);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
}

export function formatSourceTypeLabel(sourceType: SourceType | string): string {
  switch (sourceType) {
    case 'manual':
      return 'Manual Intake';
    case 'authorized_feed':
      return 'Authorized Feed';
    case 'notification_import':
      return 'Notification Import';
    case 'official_api':
      return 'Official API';
    default:
      return sourceType;
  }
}

export function extractErrorInfo(err: unknown): {
  message: string;
  code?: string;
  requestId?: string;
} {
  if (err instanceof ApiError) {
    return {
      message: err.message,
      code: err.code,
      requestId: err.requestId,
    };
  }
  if (err instanceof Error) {
    return { message: err.message };
  }
  return { message: 'An unexpected error occurred.' };
}

export function getActivityMetadata(log: ActivityLog): Record<string, unknown> {
  return log.metadata ?? log.metadata_json ?? {};
}

export function classifyActivityOutcome(
  eventType: string
): 'success' | 'skipped' | 'failed' {
  const lower = eventType.toLowerCase();
  if (lower.includes('fail') || lower.includes('error')) return 'failed';
  if (lower.includes('skip')) return 'skipped';
  return 'success';
}

export function formatActivityLabel(eventType: string): string {
  const labels: Record<string, string> = {
    target_created: 'Watchlist target added',
    target_updated: 'Watchlist target updated',
    target_deleted: 'Watchlist target removed',
    post_ingested_manual: 'Post submitted manually',
    draft_generated: 'Comment draft generated',
    draft_edited: 'Draft edited',
    draft_regenerated: 'Draft regenerated',
    draft_copied: 'Draft copied to clipboard',
    draft_opened: 'Original post opened',
    draft_skipped: 'Draft skipped',
    draft_archived: 'Draft archived',
    draft_deleted: 'Draft deleted',
    preferences_updated: 'Comment preferences updated',
    style_sample_added: 'Style sample added',
    style_sample_deleted: 'Style sample removed',
    telegram_connect_initiated: 'Telegram verification started',
    telegram_connected: 'Telegram connected',
    telegram_disconnected: 'Telegram disconnected',
    telegram_test_sent: 'Telegram test notification sent',
    telegram_test_failed: 'Telegram test notification failed',
    notification_settings_updated: 'Notification settings updated',
    source_check_failed: 'Source check failed',
    source_check_succeeded: 'Source check succeeded',
    profile_updated: 'Profile updated',
  };
  return labels[eventType] || eventType.replace(/_/g, ' ');
}
