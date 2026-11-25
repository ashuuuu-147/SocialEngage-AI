-- ============================================================================
-- SocialEngage AI — Migration 001: Initial Supabase PostgreSQL Schema
-- Matches DATABASE_SCHEMA.md with resolved dedupe_key, post status, and
-- standalone manual-post ownership (submitted_by_user_id).
-- ============================================================================

create extension if not exists "pgcrypto";

-- 1. profiles (linked 1:1 to Supabase auth.users)
create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  timezone text not null default 'Asia/Kolkata',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- 2. tracked_targets
create table if not exists public.tracked_targets (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  platform text not null check (platform in ('linkedin', 'instagram')),
  profile_url text not null,
  display_name text,
  source_type text not null check (source_type in ('official_api', 'authorized_feed', 'notification_import', 'manual')),
  external_profile_id text,
  status text not null default 'active' check (status in ('active', 'paused', 'unsupported', 'error')),
  preferences jsonb not null default '{}'::jsonb,
  last_checked_at timestamptz,
  last_success_at timestamptz,
  last_error_code text,
  created_at timestamptz not null default now(),
  constraint uq_tracked_targets_user_platform_url unique (user_id, platform, profile_url)
);

-- 3. posts
create table if not exists public.posts (
  id uuid primary key default gen_random_uuid(),
  platform text not null check (platform in ('linkedin', 'instagram')),
  source_post_id text,
  canonical_url text not null,
  dedupe_key text not null,
  submitted_by_user_id uuid references public.profiles(id) on delete set null,
  author_name text,
  author_url text,
  content_text text,
  media_type text,
  status text not null default 'discovered' check (status in ('discovered', 'analyzing', 'drafted', 'skipped', 'error')),
  published_at timestamptz,
  detected_at timestamptz not null default now(),
  content_hash text,
  source_metadata jsonb not null default '{}'::jsonb,
  constraint uq_posts_dedupe_key unique (dedupe_key)
);

-- 4. target_posts
create table if not exists public.target_posts (
  id uuid primary key default gen_random_uuid(),
  target_id uuid not null references public.tracked_targets(id) on delete cascade,
  post_id uuid not null references public.posts(id) on delete cascade,
  detected_at timestamptz not null default now(),
  constraint uq_target_posts_target_post unique (target_id, post_id)
);

-- 4b. user_posts (associates manually ingested posts with submitting users for RLS isolation)
create table if not exists public.user_posts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  post_id uuid not null references public.posts(id) on delete cascade,
  created_at timestamptz not null default now(),
  constraint uq_user_posts_user_post unique (user_id, post_id)
);

-- 5. comment_drafts
create table if not exists public.comment_drafts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  post_id uuid not null references public.posts(id) on delete cascade,
  draft_text text not null,
  edited_text text,
  style_variant text,
  relevance_score numeric(5, 2),
  quality_score numeric(5, 2),
  status text not null default 'pending' check (status in ('pending', 'edited', 'copied', 'opened', 'skipped', 'archived')),
  generation_model text,
  generation_metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- 6. user_preferences
create table if not exists public.user_preferences (
  user_id uuid primary key references public.profiles(id) on delete cascade,
  tone text not null default 'professional-conversational',
  length text not null default 'short',
  language text not null default 'English',
  emoji_level text not null default 'low',
  relevance_threshold numeric(5, 2) not null default 0.70,
  avoid_phrases text[] not null default '{}',
  preferred_topics text[] not null default '{}',
  excluded_topics text[] not null default '{}',
  monitoring_interval_minutes integer not null default 30,
  data_retention_days integer not null default 90,
  updated_at timestamptz not null default now()
);

-- 7. style_samples
create table if not exists public.style_samples (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  sample_text text not null,
  created_at timestamptz not null default now()
);

-- 8. notification_settings
create table if not exists public.notification_settings (
  user_id uuid primary key references public.profiles(id) on delete cascade,
  telegram_chat_id text,
  telegram_enabled boolean not null default false,
  telegram_verification_code text,
  telegram_verification_expires_at timestamptz,
  daily_digest_enabled boolean not null default false,
  digest_time time not null default '19:00',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- 9. monitoring_jobs
create table if not exists public.monitoring_jobs (
  id uuid primary key default gen_random_uuid(),
  target_id uuid not null references public.tracked_targets(id) on delete cascade,
  status text not null check (status in ('queued', 'running', 'success', 'partial', 'failed')),
  started_at timestamptz,
  finished_at timestamptz,
  items_found integer not null default 0,
  error_code text,
  error_summary text,
  created_at timestamptz not null default now()
);

-- 10. activity_logs
create table if not exists public.activity_logs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  event_type text not null,
  entity_type text,
  entity_id uuid,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
