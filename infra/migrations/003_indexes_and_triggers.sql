-- ============================================================================
-- SocialEngage AI — Migration 003: Indexes, Triggers & Auth Bootstrap
-- ============================================================================

-- Performance indexes
create index if not exists idx_tracked_targets_user_status
  on public.tracked_targets (user_id, status);

create index if not exists idx_posts_platform_detected
  on public.posts (platform, detected_at desc);

create index if not exists idx_target_posts_target_detected
  on public.target_posts (target_id, detected_at desc);

create index if not exists idx_comment_drafts_user_status_created
  on public.comment_drafts (user_id, status, created_at desc);

create index if not exists idx_monitoring_jobs_target_created
  on public.monitoring_jobs (target_id, created_at desc);

create index if not exists idx_activity_logs_user_created
  on public.activity_logs (user_id, created_at desc);

-- Updated-at trigger helper
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_profiles_updated_at on public.profiles;
create trigger trg_profiles_updated_at
  before update on public.profiles
  for each row execute function public.set_updated_at();

drop trigger if exists trg_comment_drafts_updated_at on public.comment_drafts;
create trigger trg_comment_drafts_updated_at
  before update on public.comment_drafts
  for each row execute function public.set_updated_at();

drop trigger if exists trg_user_preferences_updated_at on public.user_preferences;
create trigger trg_user_preferences_updated_at
  before update on public.user_preferences
  for each row execute function public.set_updated_at();

drop trigger if exists trg_notification_settings_updated_at on public.notification_settings;
create trigger trg_notification_settings_updated_at
  before update on public.notification_settings
  for each row execute function public.set_updated_at();

-- Bootstrap profile, preferences, and notification settings when a Supabase auth user signs up
create or replace function public.handle_new_auth_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, display_name)
  values (new.id, coalesce(new.raw_user_meta_data ->> 'display_name', split_part(new.email, '@', 1)))
  on conflict (id) do nothing;

  insert into public.user_preferences (user_id)
  values (new.id)
  on conflict (user_id) do nothing;

  insert into public.notification_settings (user_id)
  values (new.id)
  on conflict (user_id) do nothing;

  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_auth_user();
