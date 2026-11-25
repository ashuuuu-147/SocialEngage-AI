import type {
  ActivityLog,
  DraftWithPost,
  MonitoringJob,
  NotificationSettings,
  OverviewData,
  Post,
  Preferences,
  SourceCapability,
  StyleSample,
  Target,
  UserProfile,
} from './types';

const DEMO_USER_ID = '00000000-0000-0000-0000-000000000001';
const nowIso = new Date().toISOString();
const hoursAgo = (h: number) => new Date(Date.now() - h * 3600_000).toISOString();

export interface DemoStore {
  profile: UserProfile;
  preferences: Preferences;
  notifications: NotificationSettings;
  styleSamples: StyleSample[];
  targets: Target[];
  posts: Post[];
  drafts: DraftWithPost[];
  activity: ActivityLog[];
  jobs: MonitoringJob[];
  capabilities: SourceCapability[];
}

export function createInitialDemoStore(): DemoStore {
  const target1Id = '11111111-1111-1111-1111-111111111101';
  const target2Id = '11111111-1111-1111-1111-111111111102';
  const target3Id = '11111111-1111-1111-1111-111111111103';

  const post1Id = '22222222-2222-2222-2222-222222222201';
  const post2Id = '22222222-2222-2222-2222-222222222202';

  const draft1Id = '33333333-3333-3333-3333-333333333301';
  const draft2Id = '33333333-3333-3333-3333-333333333302';

  const targets: Target[] = [
    {
      id: target1Id,
      user_id: DEMO_USER_ID,
      platform: 'linkedin',
      profile_url: 'https://www.linkedin.com/in/maya-lin-product',
      display_name: 'Maya Lin (Product Ops)',
      source_type: 'manual',
      external_profile_id: null,
      status: 'active',
      preferences: {},
      last_checked_at: hoursAgo(1),
      last_success_at: hoursAgo(1),
      last_error_code: null,
      created_at: hoursAgo(72),
      capability: {
        source_type: 'manual',
        supported: true,
        reason: 'Manual post URL and text intake is always available and compliant.',
        documentation_note: 'Submit permitted post URLs and preview text directly.',
        requires_manual_fallback: false,
      },
    },
    {
      id: target2Id,
      user_id: DEMO_USER_ID,
      platform: 'linkedin',
      profile_url: 'https://www.linkedin.com/company/cloud-builders-hq',
      display_name: 'Cloud Builders HQ',
      source_type: 'authorized_feed',
      external_profile_id: null,
      status: 'active',
      preferences: { feed_url: 'https://example.com/cloud-builders/feed.xml' },
      last_checked_at: hoursAgo(2),
      last_success_at: hoursAgo(2),
      last_error_code: null,
      created_at: hoursAgo(96),
      capability: {
        source_type: 'authorized_feed',
        supported: true,
        reason: 'Supported when a user-authorized RSS/Atom feed URL is configured.',
        documentation_note: 'Fetches only explicit feed_url provided by the user.',
        requires_manual_fallback: false,
      },
    },
    {
      id: target3Id,
      user_id: DEMO_USER_ID,
      platform: 'instagram',
      profile_url: 'https://www.instagram.com/designsystems.weekly',
      display_name: 'Design Systems Weekly',
      source_type: 'official_api',
      external_profile_id: null,
      status: 'unsupported',
      preferences: {},
      last_checked_at: hoursAgo(4),
      last_success_at: null,
      last_error_code: 'SOURCE_UNAVAILABLE',
      created_at: hoursAgo(48),
      capability: {
        source_type: 'official_api',
        supported: false,
        reason: 'Third-party creator timelines are restricted under official Instagram API permissions.',
        documentation_note: 'Use Manual Post URL intake or Notification Import instead.',
        requires_manual_fallback: true,
      },
    },
  ];

  const post1Drafts = [
    {
      id: draft1Id,
      user_id: DEMO_USER_ID,
      post_id: post1Id,
      draft_text:
        'Moving background jobs to cloud schedules eliminates so much silent laptop friction. Did you pair idempotency keys with the cron triggers or handle dedupe at the queue layer?',
      edited_text: null,
      style_variant: 'insightful-question',
      relevance_score: 0.91,
      quality_score: 0.88,
      status: 'pending' as const,
      generation_model: 'offline-preview',
      generation_metadata: { topic: 'cloud-automation' },
      created_at: hoursAgo(2),
      updated_at: hoursAgo(2),
    },
  ];

  const post2Drafts = [
    {
      id: draft2Id,
      user_id: DEMO_USER_ID,
      post_id: post2Id,
      draft_text:
        'Keeping spacing tokens on an 8px rhythm makes cross-breakpoint reviews far calmer—especially when moving from multi-column desktop cards down to mobile drawers.',
      edited_text: null,
      style_variant: 'concise-observation',
      relevance_score: 0.84,
      quality_score: 0.86,
      status: 'copied' as const,
      generation_model: 'offline-preview',
      generation_metadata: { topic: 'design-systems' },
      created_at: hoursAgo(8),
      updated_at: hoursAgo(6),
    },
  ];

  const posts: Post[] = [
    {
      id: post1Id,
      platform: 'linkedin',
      source_post_id: '7264920182',
      canonical_url: 'https://www.linkedin.com/feed/update/urn:li:activity:7264920182',
      author_name: 'Maya Lin (Product Ops)',
      author_url: 'https://www.linkedin.com/in/maya-lin-product',
      content_text:
        'We moved all our recurring workspace sync jobs from local cron scripts to managed cloud triggers this week. Zero missed runs when someone closes their laptop, and every retry is idempotent.',
      media_type: 'text',
      status: 'drafted',
      published_at: hoursAgo(3),
      detected_at: hoursAgo(2),
      source_metadata: { intake_method: 'manual' },
      drafts: post1Drafts,
    },
    {
      id: post2Id,
      platform: 'instagram',
      source_post_id: 'C9xDemoPost2',
      canonical_url: 'https://www.instagram.com/p/C9xDemoPost2/',
      author_name: 'Design Systems Weekly',
      author_url: 'https://www.instagram.com/designsystems.weekly',
      content_text:
        'Calm SaaS interfaces start with restraint: subtle neutral surfaces, an 8px spacing grid, and status badges that pair icons with clear labels instead of relying on color alone.',
      media_type: 'carousel',
      status: 'drafted',
      published_at: hoursAgo(10),
      detected_at: hoursAgo(9),
      source_metadata: { intake_method: 'manual' },
      drafts: post2Drafts,
    },
  ];

  const drafts: DraftWithPost[] = [
    { ...post1Drafts[0], post: { ...posts[0], drafts: [] } },
    { ...post2Drafts[0], post: { ...posts[1], drafts: [] } },
  ];

  const activity: ActivityLog[] = [
    {
      id: '44444444-4444-4444-4444-444444444401',
      user_id: DEMO_USER_ID,
      event_type: 'draft_generated',
      entity_type: 'draft',
      entity_id: draft1Id,
      metadata: { platform: 'linkedin', relevance_score: 0.91 },
      created_at: hoursAgo(2),
    },
    {
      id: '44444444-4444-4444-4444-444444444402',
      user_id: DEMO_USER_ID,
      event_type: 'source_check_failed',
      entity_type: 'target',
      entity_id: target3Id,
      metadata: {
        error_code: 'SOURCE_UNAVAILABLE',
        reason: 'Official Instagram API does not permit reading third-party creator timelines.',
      },
      created_at: hoursAgo(4),
    },
    {
      id: '44444444-4444-4444-4444-444444444403',
      user_id: DEMO_USER_ID,
      event_type: 'draft_skipped',
      entity_type: 'post',
      entity_id: null,
      metadata: { reason: 'Post matched excluded topic: giveaway' },
      created_at: hoursAgo(5),
    },
    {
      id: '44444444-4444-4444-4444-444444444404',
      user_id: DEMO_USER_ID,
      event_type: 'draft_copied',
      entity_type: 'draft',
      entity_id: draft2Id,
      metadata: { platform: 'instagram' },
      created_at: hoursAgo(6),
    },
  ];

  const jobs: MonitoringJob[] = [
    {
      id: '55555555-5555-5555-5555-555555555501',
      target_id: target2Id,
      status: 'succeeded',
      started_at: hoursAgo(2),
      finished_at: hoursAgo(2),
      items_found: 1,
      error_code: null,
      error_summary: null,
      created_at: hoursAgo(2),
    },
    {
      id: '55555555-5555-5555-5555-555555555502',
      target_id: target3Id,
      status: 'failed',
      started_at: hoursAgo(4),
      finished_at: hoursAgo(4),
      items_found: 0,
      error_code: 'SOURCE_UNAVAILABLE',
      error_summary: 'Official API access for third-party Instagram profiles is unavailable. Use Manual intake.',
      created_at: hoursAgo(4),
    },
  ];

  const capabilities: SourceCapability[] = [
    {
      platform: 'linkedin',
      source_type: 'manual',
      supported: true,
      reason: 'Manual post URL and text intake is always available and compliant.',
      documentation_note: 'Submit permitted post URLs and preview text directly.',
      requires_manual_fallback: false,
    },
    {
      platform: 'linkedin',
      source_type: 'authorized_feed',
      supported: true,
      reason: 'Supported when a user-authorized RSS/Atom feed URL is configured in target preferences.',
      documentation_note: 'Fetches only explicit feed_url provided by the user.',
      requires_manual_fallback: false,
    },
    {
      platform: 'linkedin',
      source_type: 'notification_import',
      supported: true,
      reason: 'Batch import posts from user-authorized email or webhook notifications.',
      documentation_note: 'Never scrapes platform HTML.',
      requires_manual_fallback: false,
    },
    {
      platform: 'linkedin',
      source_type: 'official_api',
      supported: false,
      reason: 'Third-party LinkedIn profile feeds require partner-approved Organization/Member API access.',
      documentation_note: 'Use Manual intake or Authorized Feed unless an official API token is configured.',
      requires_manual_fallback: true,
    },
    {
      platform: 'instagram',
      source_type: 'manual',
      supported: true,
      reason: 'Manual post URL and text intake is always available and compliant.',
      documentation_note: 'Submit permitted post URLs and preview text directly.',
      requires_manual_fallback: false,
    },
    {
      platform: 'instagram',
      source_type: 'authorized_feed',
      supported: true,
      reason: 'Supported when a user-authorized RSS/Atom feed URL is configured.',
      documentation_note: 'Fetches only explicit feed_url provided by the user.',
      requires_manual_fallback: false,
    },
    {
      platform: 'instagram',
      source_type: 'notification_import',
      supported: true,
      reason: 'Batch import posts from user-authorized notifications.',
      documentation_note: 'Never scrapes platform HTML.',
      requires_manual_fallback: false,
    },
    {
      platform: 'instagram',
      source_type: 'official_api',
      supported: false,
      reason: 'Instagram Graph API does not allow reading arbitrary third-party creator timelines.',
      documentation_note: 'Use Manual post intake or Notification Import instead.',
      requires_manual_fallback: true,
    },
  ];

  return {
    profile: {
      id: DEMO_USER_ID,
      display_name: 'Demo Preview Workspace',
      timezone: 'Asia/Kolkata',
      created_at: hoursAgo(120),
    },
    preferences: {
      user_id: DEMO_USER_ID,
      tone: 'professional-conversational',
      length: 'short',
      language: 'English',
      emoji_level: 'low',
      relevance_threshold: 0.7,
      avoid_phrases: ['great post!', 'love this!'],
      preferred_topics: ['cloud architecture', 'product engineering', 'design systems'],
      excluded_topics: ['giveaway', 'crypto'],
      monitoring_interval_minutes: 30,
      data_retention_days: 90,
      updated_at: nowIso,
    },
    notifications: {
      user_id: DEMO_USER_ID,
      telegram_enabled: false,
      telegram_connected: false,
      telegram_chat_id_masked: null,
      daily_digest_enabled: true,
      digest_time: '09:00:00',
      updated_at: nowIso,
    },
    styleSamples: [
      {
        id: '66666666-6666-6666-6666-666666666601',
        user_id: DEMO_USER_ID,
        sample_text:
          'Really appreciate the concrete latency numbers here—did you notice any cold-start trade-offs once you moved to scheduled workers?',
        created_at: hoursAgo(48),
      },
    ],
    targets,
    posts,
    drafts,
    activity,
    jobs,
    capabilities,
  };
}

export function buildDemoOverview(store: DemoStore): OverviewData {
  const active = store.targets.filter((t) => t.status === 'active').length;
  const unsupported = store.targets.filter(
    (t) => t.status === 'unsupported' || t.status === 'error'
  ).length;
  const awaiting = store.drafts.filter(
    (d) => d.status === 'pending' || d.status === 'edited'
  ).length;
  const approved = store.drafts.filter(
    (d) => d.status === 'copied' || d.status === 'opened'
  ).length;
  const health = store.targets.some((t) => t.status === 'error')
    ? 'degraded'
    : active > 0
      ? 'healthy'
      : 'idle';

  return {
    tracked_profiles: store.targets.length,
    active_profiles: active,
    unsupported_profiles: unsupported,
    new_posts_detected: store.posts.length,
    drafts_awaiting_review: awaiting,
    drafts_approved_or_copied: approved,
    monitoring_health: health,
    last_checked_at: store.targets[0]?.last_checked_at ?? null,
    recent_activity: store.activity.slice(0, 8),
  };
}
