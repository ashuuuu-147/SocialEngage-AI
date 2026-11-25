-- ============================================================================
-- SocialEngage AI — Migration 002: Row-Level Security (RLS) Policies
-- Enforces strict user-level data isolation across all tables.
-- ============================================================================

alter table public.profiles enable row level security;
alter table public.tracked_targets enable row level security;
alter table public.posts enable row level security;
alter table public.target_posts enable row level security;
alter table public.user_posts enable row level security;
alter table public.comment_drafts enable row level security;
alter table public.user_preferences enable row level security;
alter table public.style_samples enable row level security;
alter table public.notification_settings enable row level security;
alter table public.monitoring_jobs enable row level security;
alter table public.activity_logs enable row level security;

-- profiles
create policy "profiles_select_own" on public.profiles
  for select using (auth.uid() = id);
create policy "profiles_insert_own" on public.profiles
  for insert with check (auth.uid() = id);
create policy "profiles_update_own" on public.profiles
  for update using (auth.uid() = id) with check (auth.uid() = id);
create policy "profiles_delete_own" on public.profiles
  for delete using (auth.uid() = id);

-- tracked_targets
create policy "targets_select_own" on public.tracked_targets
  for select using (auth.uid() = user_id);
create policy "targets_insert_own" on public.tracked_targets
  for insert with check (auth.uid() = user_id);
create policy "targets_update_own" on public.tracked_targets
  for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "targets_delete_own" on public.tracked_targets
  for delete using (auth.uid() = user_id);

-- posts: visible if submitted by the user, linked in user_posts, OR associated with one of the user's tracked_targets
create policy "posts_select_accessible" on public.posts
  for select using (
    submitted_by_user_id = auth.uid()
    or exists (
      select 1 from public.user_posts up
      where up.post_id = posts.id and up.user_id = auth.uid()
    )
    or exists (
      select 1
      from public.target_posts tp
      join public.tracked_targets tt on tt.id = tp.target_id
      where tp.post_id = posts.id and tt.user_id = auth.uid()
    )
  );
create policy "posts_insert_own_manual" on public.posts
  for insert with check (submitted_by_user_id = auth.uid());

-- user_posts
create policy "user_posts_select_own" on public.user_posts
  for select using (auth.uid() = user_id);
create policy "user_posts_insert_own" on public.user_posts
  for insert with check (auth.uid() = user_id);
create policy "user_posts_delete_own" on public.user_posts
  for delete using (auth.uid() = user_id);

-- target_posts: owned through tracked_targets
create policy "target_posts_select_own" on public.target_posts
  for select using (
    exists (
      select 1 from public.tracked_targets tt
      where tt.id = target_posts.target_id and tt.user_id = auth.uid()
    )
  );
create policy "target_posts_insert_own" on public.target_posts
  for insert with check (
    exists (
      select 1 from public.tracked_targets tt
      where tt.id = target_posts.target_id and tt.user_id = auth.uid()
    )
  );
create policy "target_posts_delete_own" on public.target_posts
  for delete using (
    exists (
      select 1 from public.tracked_targets tt
      where tt.id = target_posts.target_id and tt.user_id = auth.uid()
    )
  );

-- comment_drafts
create policy "drafts_select_own" on public.comment_drafts
  for select using (auth.uid() = user_id);
create policy "drafts_insert_own" on public.comment_drafts
  for insert with check (auth.uid() = user_id);
create policy "drafts_update_own" on public.comment_drafts
  for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "drafts_delete_own" on public.comment_drafts
  for delete using (auth.uid() = user_id);

-- user_preferences
create policy "preferences_select_own" on public.user_preferences
  for select using (auth.uid() = user_id);
create policy "preferences_insert_own" on public.user_preferences
  for insert with check (auth.uid() = user_id);
create policy "preferences_update_own" on public.user_preferences
  for update using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- style_samples
create policy "style_samples_select_own" on public.style_samples
  for select using (auth.uid() = user_id);
create policy "style_samples_insert_own" on public.style_samples
  for insert with check (auth.uid() = user_id);
create policy "style_samples_delete_own" on public.style_samples
  for delete using (auth.uid() = user_id);

-- notification_settings
create policy "notifications_select_own" on public.notification_settings
  for select using (auth.uid() = user_id);
create policy "notifications_insert_own" on public.notification_settings
  for insert with check (auth.uid() = user_id);
create policy "notifications_update_own" on public.notification_settings
  for update using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- monitoring_jobs: read-only visibility for owning user; writes handled by service role
create policy "monitoring_jobs_select_own" on public.monitoring_jobs
  for select using (
    exists (
      select 1 from public.tracked_targets tt
      where tt.id = monitoring_jobs.target_id and tt.user_id = auth.uid()
    )
  );

-- activity_logs
create policy "activity_logs_select_own" on public.activity_logs
  for select using (auth.uid() = user_id);
create policy "activity_logs_insert_own" on public.activity_logs
  for insert with check (auth.uid() = user_id);
