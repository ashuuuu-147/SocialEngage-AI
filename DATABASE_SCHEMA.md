# Database Schema
## Supabase PostgreSQL

Use UUID primary keys and UTC timestamps. Enable Row Level Security (RLS) on all user-owned tables.

## 1. `profiles`
Application profile linked to auth user.
- `id uuid primary key references auth.users(id) on delete cascade`
- `display_name text`
- `timezone text default 'Asia/Kolkata'`
- `created_at timestamptz default now()`
- `updated_at timestamptz default now()`

## 2. `tracked_targets`
- `id uuid primary key default gen_random_uuid()`
- `user_id uuid not null references profiles(id) on delete cascade`
- `platform text not null check (platform in ('linkedin','instagram'))`
- `profile_url text not null`
- `display_name text`
- `source_type text not null check (source_type in ('official_api','authorized_feed','notification_import','manual'))`
- `external_profile_id text`
- `status text not null default 'active' check (status in ('active','paused','unsupported','error'))`
- `preferences jsonb not null default '{}'`
- `last_checked_at timestamptz`
- `last_success_at timestamptz`
- `last_error_code text`
- `created_at timestamptz default now()`
- Unique: `(user_id, platform, profile_url)`

## 3. `posts`
- `id uuid primary key default gen_random_uuid()`
- `platform text not null`
- `source_post_id text`
- `canonical_url text not null`
- `author_name text`
- `author_url text`
- `content_text text`
- `media_type text`
- `published_at timestamptz`
- `detected_at timestamptz default now()`
- `content_hash text`
- `source_metadata jsonb not null default '{}'`
- Unique key should be `(platform, source_post_id)` when ID exists; otherwise `(platform, canonical_url)` through application-level normalized key or separate generated `dedupe_key`.

## 4. `target_posts`
Associates a post with one or more targets.
- `id uuid primary key default gen_random_uuid()`
- `target_id uuid references tracked_targets(id) on delete cascade`
- `post_id uuid references posts(id) on delete cascade`
- `detected_at timestamptz default now()`
- Unique `(target_id, post_id)`

## 5. `comment_drafts`
- `id uuid primary key default gen_random_uuid()`
- `user_id uuid not null references profiles(id) on delete cascade`
- `post_id uuid not null references posts(id) on delete cascade`
- `draft_text text not null`
- `edited_text text`
- `style_variant text`
- `relevance_score numeric(5,2)`
- `quality_score numeric(5,2)`
- `status text not null default 'pending' check (status in ('pending','edited','copied','opened','skipped','archived'))`
- `generation_model text`
- `generation_metadata jsonb not null default '{}'`
- `created_at timestamptz default now()`
- `updated_at timestamptz default now()`
- Index `(user_id, status, created_at desc)`

## 6. `user_preferences`
- `user_id uuid primary key references profiles(id) on delete cascade`
- `tone text default 'professional-conversational'`
- `length text default 'short'`
- `language text default 'English'`
- `emoji_level text default 'low'`
- `relevance_threshold numeric(5,2) default 0.70`
- `avoid_phrases text[] default '{}'`
- `preferred_topics text[] default '{}'`
- `excluded_topics text[] default '{}'`
- `updated_at timestamptz default now()`

## 7. `style_samples`
- `id uuid primary key default gen_random_uuid()`
- `user_id uuid not null references profiles(id) on delete cascade`
- `sample_text text not null`
- `created_at timestamptz default now()`

## 8. `notification_settings`
- `user_id uuid primary key references profiles(id) on delete cascade`
- `telegram_chat_id text`
- `telegram_enabled boolean default false`
- `daily_digest_enabled boolean default false`
- `digest_time time default '19:00'`
- `created_at timestamptz default now()`
- `updated_at timestamptz default now()`

## 9. `monitoring_jobs`
- `id uuid primary key default gen_random_uuid()`
- `target_id uuid references tracked_targets(id) on delete cascade`
- `status text check (status in ('queued','running','success','partial','failed'))`
- `started_at timestamptz`
- `finished_at timestamptz`
- `items_found integer default 0`
- `error_code text`
- `error_summary text`
- `created_at timestamptz default now()`

## 10. `activity_logs`
- `id uuid primary key default gen_random_uuid()`
- `user_id uuid not null references profiles(id) on delete cascade`
- `event_type text not null`
- `entity_type text`
- `entity_id uuid`
- `metadata jsonb not null default '{}'`
- `created_at timestamptz default now()`

## RLS policy guidance
- Users can select/update/delete only rows belonging to their `user_id`.
- Child tables must enforce ownership through joins or secured RPCs.
- Service-role credentials stay server-side and must never be exposed to the frontend.
- Do not rely on frontend filtering for security.
