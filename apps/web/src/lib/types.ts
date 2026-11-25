export type PlatformType = 'linkedin' | 'instagram';
export type SourceType = 'official_api' | 'authorized_feed' | 'notification_import' | 'manual';
export type TargetStatus = 'active' | 'paused' | 'unsupported' | 'error';
export type DraftStatus = 'pending' | 'edited' | 'copied' | 'opened' | 'skipped' | 'archived';
export type DraftAction = 'copied' | 'opened' | 'skipped' | 'archived';
export type MonitoringHealth = 'healthy' | 'degraded' | 'idle';

export type NavSection =
  | 'overview'
  | 'watchlist'
  | 'inbox'
  | 'drafts'
  | 'activity'
  | 'settings';

export interface BackendErrorEnvelope {
  error: {
    code: string;
    message: string;
    request_id?: string;
  };
}

export interface SourceCapability {
  platform?: PlatformType;
  source_type: SourceType;
  supported: boolean;
  reason: string;
  documentation_note: string;
  requires_manual_fallback: boolean;
}

export interface Target {
  id: string;
  user_id: string;
  platform: PlatformType;
  profile_url: string;
  display_name: string | null;
  source_type: SourceType;
  external_profile_id: string | null;
  status: TargetStatus;
  preferences: Record<string, unknown>;
  last_checked_at: string | null;
  last_success_at: string | null;
  last_error_code: string | null;
  created_at: string;
  capability: SourceCapability | null;
}

export interface TargetCreateRequest {
  platform: PlatformType;
  profile_url: string;
  display_name?: string;
  source_type: SourceType;
  external_profile_id?: string;
  preferences?: Record<string, unknown>;
}

export interface TargetUpdateRequest {
  display_name?: string;
  status?: 'active' | 'paused';
  source_type?: SourceType;
  preferences?: Record<string, unknown>;
}

export interface DraftSummary {
  id: string;
  user_id: string;
  post_id: string;
  draft_text: string;
  edited_text: string | null;
  style_variant: string | null;
  relevance_score: number | null;
  quality_score: number | null;
  status: DraftStatus;
  generation_model: string | null;
  generation_metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface Post {
  id: string;
  platform: PlatformType;
  source_post_id: string | null;
  canonical_url: string;
  author_name: string | null;
  author_url: string | null;
  content_text: string | null;
  media_type: string | null;
  status: string;
  published_at: string | null;
  detected_at: string;
  source_metadata: Record<string, unknown>;
  drafts: DraftSummary[];
}

export interface DraftWithPost extends DraftSummary {
  post: Post | null;
}

export interface ManualPostIngestRequest {
  platform: PlatformType;
  post_url: string;
  target_id?: string;
  author_name?: string;
  content_text?: string;
  media_type?: string;
  published_at?: string;
  auto_generate_drafts: boolean;
}

export interface NotificationImportRequest {
  target_id: string;
  posts: ManualPostIngestRequest[];
}

export interface DraftGenerateRequest {
  variants?: number;
  tone?: string;
  length?: 'short' | 'medium' | 'detailed';
  language?: string;
}

export interface DraftUpdateRequest {
  edited_text?: string;
  status?: DraftStatus;
}

export interface DraftRegenerateRequest {
  tone?: string;
  length?: 'short' | 'medium' | 'detailed';
  instruction?: string;
}

export interface Preferences {
  user_id: string;
  tone: string;
  length: 'short' | 'medium' | 'detailed' | string;
  language: string;
  emoji_level: 'none' | 'low' | 'medium' | string;
  relevance_threshold: number;
  avoid_phrases: string[];
  preferred_topics: string[];
  excluded_topics: string[];
  monitoring_interval_minutes: number;
  data_retention_days: number;
  updated_at: string;
}

export interface PreferencesUpdateRequest {
  tone?: string;
  length?: 'short' | 'medium' | 'detailed';
  language?: string;
  emoji_level?: 'none' | 'low' | 'medium';
  relevance_threshold?: number;
  avoid_phrases?: string[];
  preferred_topics?: string[];
  excluded_topics?: string[];
  monitoring_interval_minutes?: number;
  data_retention_days?: number;
}

export interface StyleSample {
  id: string;
  user_id: string;
  sample_text: string;
  created_at: string;
}

export interface NotificationSettings {
  user_id: string;
  telegram_enabled: boolean;
  telegram_connected: boolean;
  telegram_chat_id_masked: string | null;
  daily_digest_enabled: boolean;
  digest_time: string;
  updated_at: string;
}

export interface NotificationSettingsUpdateRequest {
  telegram_enabled?: boolean;
  daily_digest_enabled?: boolean;
  digest_time?: string;
}

export interface TelegramConnectResponse {
  verification_code: string;
  expires_at: string;
  bot_username: string | null;
  deep_link_url: string | null;
  instructions: string;
}

export interface TelegramVerifyRequest {
  verification_code: string;
  chat_id: string;
}

export interface ActivityLog {
  id: string;
  user_id: string;
  event_type: string;
  entity_type: string | null;
  entity_id: string | null;
  metadata?: Record<string, unknown>;
  metadata_json?: Record<string, unknown>;
  created_at: string;
}

export interface MonitoringJob {
  id: string;
  target_id: string;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  items_found: number;
  error_code: string | null;
  error_summary: string | null;
  created_at: string;
}

export interface OverviewData {
  tracked_profiles: number;
  active_profiles: number;
  unsupported_profiles: number;
  new_posts_detected: number;
  drafts_awaiting_review: number;
  drafts_approved_or_copied: number;
  monitoring_health: MonitoringHealth;
  last_checked_at: string | null;
  recent_activity: ActivityLog[];
}

export interface UserProfile {
  id: string;
  display_name: string | null;
  timezone: string;
  created_at: string;
}

export interface HealthStatus {
  status: string;
  service: string;
  env: string;
  ai_provider: string;
  dev_auth_bypass: boolean;
}
