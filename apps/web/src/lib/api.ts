import { buildDemoOverview, createInitialDemoStore, type DemoStore } from './demoData';
import type {
  ActivityLog,
  BackendErrorEnvelope,
  DraftAction,
  DraftGenerateRequest,
  DraftRegenerateRequest,
  DraftSummary,
  DraftUpdateRequest,
  DraftWithPost,
  HealthStatus,
  ManualPostIngestRequest,
  MonitoringJob,
  NotificationImportRequest,
  NotificationSettings,
  NotificationSettingsUpdateRequest,
  OverviewData,
  Post,
  Preferences,
  PreferencesUpdateRequest,
  SourceCapability,
  StyleSample,
  Target,
  TargetCreateRequest,
  TargetUpdateRequest,
  TelegramConnectResponse,
  TelegramVerifyRequest,
  UserProfile,
} from './types';

export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(/\/+$/, '');

export interface AuthCredentials {
  mode: 'jwt' | 'dev' | 'demo';
  token?: string;
  devUserId?: string;
}

export class ApiError extends Error {
  code: string;
  status: number;
  requestId?: string;

  constructor(code: string, message: string, status: number, requestId?: string) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
    this.requestId = requestId;
  }
}

export function getHealthUrl(): string {
  if (API_BASE_URL.endsWith('/api/v1')) {
    return `${API_BASE_URL.slice(0, -'/api/v1'.length)}/health`;
  }
  return '/health';
}

function buildQuery(params: Record<string, string | number | undefined | null>): string {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== '') {
      sp.set(k, String(v));
    }
  }
  const str = sp.toString();
  return str ? `?${str}` : '';
}

function isErrorEnvelope(val: unknown): val is BackendErrorEnvelope {
  return (
    typeof val === 'object' &&
    val !== null &&
    'error' in val &&
    typeof (val as BackendErrorEnvelope).error?.message === 'string'
  );
}

export function createApiClient(getCredentials: () => AuthCredentials | null) {
  let demoStore: DemoStore | null = null;

  function ensureDemo(): DemoStore {
    if (!demoStore) {
      demoStore = createInitialDemoStore();
    }
    return demoStore;
  }

  function isDemoMode(): boolean {
    return getCredentials()?.mode === 'demo';
  }

  async function request<T>(path: string, init: RequestInit = {}, overrideUrl?: string): Promise<T> {
    const creds = getCredentials();
    const headers = new Headers(init.headers);

    if (!headers.has('Content-Type') && init.body) {
      headers.set('Content-Type', 'application/json');
    }

    if (creds?.mode === 'jwt' && creds.token) {
      headers.set('Authorization', `Bearer ${creds.token}`);
    } else if (creds?.mode === 'dev' && creds.devUserId) {
      headers.set('X-Dev-User-Id', creds.devUserId);
    }

    const url = overrideUrl ?? `${API_BASE_URL}${path}`;
    let response: Response;
    try {
      response = await fetch(url, { ...init, headers });
    } catch (err) {
      throw new ApiError(
        'NETWORK_ERROR',
        err instanceof Error
          ? `Unable to reach the API server (${err.message}).`
          : 'Unable to reach the API server.',
        0
      );
    }

    if (response.status === 204) {
      return undefined as T;
    }

    const text = await response.text();
    let parsed: unknown = null;
    if (text) {
      try {
        parsed = JSON.parse(text);
      } catch {
        parsed = null;
      }
    }

    if (!response.ok) {
      if (isErrorEnvelope(parsed)) {
        throw new ApiError(
          parsed.error.code || 'API_ERROR',
          parsed.error.message,
          response.status,
          parsed.error.request_id
        );
      }
      throw new ApiError(
        `HTTP_${response.status}`,
        `Request failed with status ${response.status}.`,
        response.status
      );
    }

    return parsed as T;
  }

  return {
    resetDemoStore() {
      demoStore = createInitialDemoStore();
    },

    async getHealth(): Promise<HealthStatus> {
      if (isDemoMode()) {
        return {
          status: 'ok',
          service: 'socialengage-demo-preview',
          env: 'offline-preview',
          ai_provider: 'preview',
          dev_auth_bypass: true,
        };
      }
      return request<HealthStatus>('', { method: 'GET' }, getHealthUrl());
    },

    async getOverview(): Promise<OverviewData> {
      if (isDemoMode()) {
        return buildDemoOverview(ensureDemo());
      }
      return request<OverviewData>('/overview');
    },

    async listActivity(params?: { event_type?: string; limit?: number }): Promise<ActivityLog[]> {
      if (isDemoMode()) {
        const store = ensureDemo();
        const filtered = params?.event_type
          ? store.activity.filter((a) => a.event_type === params.event_type)
          : store.activity;
        return filtered.slice(0, params?.limit ?? 50);
      }
      const qs = buildQuery({ event_type: params?.event_type, limit: params?.limit });
      return request<ActivityLog[]>(`/activity${qs}`);
    },

    async listMonitoringJobs(limit = 30): Promise<MonitoringJob[]> {
      if (isDemoMode()) {
        return ensureDemo().jobs.slice(0, limit);
      }
      return request<MonitoringJob[]>(`/monitoring/jobs${buildQuery({ limit })}`);
    },

    async getProfile(): Promise<UserProfile> {
      if (isDemoMode()) {
        return { ...ensureDemo().profile };
      }
      return request<UserProfile>('/profile');
    },

    async updateProfile(payload: { display_name?: string; timezone?: string }): Promise<UserProfile> {
      if (isDemoMode()) {
        const store = ensureDemo();
        store.profile = {
          ...store.profile,
          display_name: payload.display_name ?? store.profile.display_name,
          timezone: payload.timezone ?? store.profile.timezone,
        };
        return { ...store.profile };
      }
      return request<UserProfile>('/profile', {
        method: 'PATCH',
        body: JSON.stringify(payload),
      });
    },

    async exportAccountData(): Promise<Record<string, unknown>> {
      if (isDemoMode()) {
        const store = ensureDemo();
        return {
          profile: store.profile,
          preferences: store.preferences,
          notifications: store.notifications,
          targets: store.targets,
          style_samples: store.styleSamples,
          drafts: store.drafts,
          activity_logs: store.activity,
        };
      }
      return request<Record<string, unknown>>('/account/export');
    },

    async deleteAccount(): Promise<void> {
      if (isDemoMode()) {
        demoStore = createInitialDemoStore();
        return;
      }
      return request<void>('/account', { method: 'DELETE' });
    },

    async getSourceCapabilities(): Promise<SourceCapability[]> {
      if (isDemoMode()) {
        return [...ensureDemo().capabilities];
      }
      const res = await request<{ capabilities: SourceCapability[] }>('/sources/capabilities');
      return res.capabilities;
    },

    async listTargets(params?: {
      platform?: string;
      status?: string;
      page?: number;
      limit?: number;
    }): Promise<Target[]> {
      if (isDemoMode()) {
        let items = [...ensureDemo().targets];
        if (params?.platform) items = items.filter((t) => t.platform === params.platform);
        if (params?.status) items = items.filter((t) => t.status === params.status);
        return items;
      }
      const qs = buildQuery({
        platform: params?.platform,
        status: params?.status,
        page: params?.page,
        limit: params?.limit,
      });
      return request<Target[]>(`/targets${qs}`);
    },

    async createTarget(payload: TargetCreateRequest): Promise<Target> {
      if (isDemoMode()) {
        const store = ensureDemo();
        const cap =
          store.capabilities.find(
            (c) => c.platform === payload.platform && c.source_type === payload.source_type
          ) ?? null;
        const supported = cap ? cap.supported : true;
        const created: Target = {
          id: crypto.randomUUID(),
          user_id: store.profile.id,
          platform: payload.platform,
          profile_url: payload.profile_url,
          display_name: payload.display_name || payload.profile_url,
          source_type: payload.source_type,
          external_profile_id: payload.external_profile_id ?? null,
          status: supported ? 'active' : 'unsupported',
          preferences: payload.preferences ?? {},
          last_checked_at: null,
          last_success_at: null,
          last_error_code: supported ? null : 'SOURCE_UNAVAILABLE',
          created_at: new Date().toISOString(),
          capability: cap,
        };
        store.targets = [created, ...store.targets];
        return created;
      }
      return request<Target>('/targets', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
    },

    async updateTarget(targetId: string, payload: TargetUpdateRequest): Promise<Target> {
      if (isDemoMode()) {
        const store = ensureDemo();
        store.targets = store.targets.map((t) =>
          t.id === targetId
            ? {
                ...t,
                display_name: payload.display_name ?? t.display_name,
                status: payload.status ?? t.status,
                source_type: payload.source_type ?? t.source_type,
                preferences: payload.preferences ?? t.preferences,
              }
            : t
        );
        const found = store.targets.find((t) => t.id === targetId);
        if (!found) throw new ApiError('NOT_FOUND', 'Target not found.', 404);
        return found;
      }
      return request<Target>(`/targets/${targetId}`, {
        method: 'PATCH',
        body: JSON.stringify(payload),
      });
    },

    async deleteTarget(targetId: string): Promise<void> {
      if (isDemoMode()) {
        const store = ensureDemo();
        store.targets = store.targets.filter((t) => t.id !== targetId);
        return;
      }
      return request<void>(`/targets/${targetId}`, { method: 'DELETE' });
    },

    async checkTarget(
      targetId: string
    ): Promise<{ status: string; message?: string; summary?: Record<string, unknown> }> {
      if (isDemoMode()) {
        const store = ensureDemo();
        const target = store.targets.find((t) => t.id === targetId);
        if (!target) throw new ApiError('NOT_FOUND', 'Target not found.', 404);
        if (target.source_type === 'manual') {
          return {
            status: 'manual_only',
            message: "Manual targets do not auto-poll. Use 'Submit Post URL' to ingest a post.",
          };
        }
        target.last_checked_at = new Date().toISOString();
        return {
          status: 'completed',
          summary: { checked: 1, new_posts: 0 },
        };
      }
      return request(`/targets/${targetId}/check`, { method: 'POST' });
    },

    async ingestManualPost(payload: ManualPostIngestRequest): Promise<Post> {
      if (isDemoMode()) {
        const store = ensureDemo();
        const postId = crypto.randomUUID();
        const now = new Date().toISOString();
        const draftId = crypto.randomUUID();
        const draftSummary: DraftSummary = {
          id: draftId,
          user_id: store.profile.id,
          post_id: postId,
          draft_text: payload.content_text
            ? `Insightful take on "${payload.content_text.slice(0, 48)}..." — how are you measuring outcomes across the team?`
            : 'Thoughtful update! Curious what led to this approach.',
          edited_text: null,
          style_variant: 'insightful-question',
          relevance_score: 0.86,
          quality_score: 0.85,
          status: 'pending',
          generation_model: 'offline-preview',
          generation_metadata: { topic: 'manual-intake' },
          created_at: now,
          updated_at: now,
        };
        const drafts = payload.auto_generate_drafts && payload.content_text ? [draftSummary] : [];
        const newPost: Post = {
          id: postId,
          platform: payload.platform,
          source_post_id: null,
          canonical_url: payload.post_url,
          author_name: payload.author_name || 'Submitted Creator',
          author_url: null,
          content_text: payload.content_text ?? null,
          media_type: payload.media_type ?? 'text',
          status: drafts.length > 0 ? 'drafted' : 'new',
          published_at: payload.published_at ?? null,
          detected_at: now,
          source_metadata: { intake_method: 'manual' },
          drafts,
        };
        store.posts = [newPost, ...store.posts];
        if (drafts.length > 0) {
          store.drafts = [{ ...draftSummary, post: { ...newPost, drafts: [] } }, ...store.drafts];
        }
        return newPost;
      }
      return request<Post>('/posts/ingest-manual', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
    },

    async importNotifications(
      payload: NotificationImportRequest
    ): Promise<{ imported: number; duplicates: number }> {
      if (isDemoMode()) {
        let imported = 0;
        for (const item of payload.posts) {
          await this.ingestManualPost({ ...item, target_id: payload.target_id });
          imported += 1;
        }
        return { imported, duplicates: 0 };
      }
      return request('/posts/import-notifications', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
    },

    async listPosts(params?: {
      platform?: string;
      target_id?: string;
      status?: string;
      since?: string;
      page?: number;
      limit?: number;
    }): Promise<Post[]> {
      if (isDemoMode()) {
        let items = [...ensureDemo().posts];
        if (params?.platform) items = items.filter((p) => p.platform === params.platform);
        if (params?.status) items = items.filter((p) => p.status === params.status);
        return items;
      }
      const qs = buildQuery({
        platform: params?.platform,
        target_id: params?.target_id,
        status: params?.status,
        since: params?.since,
        page: params?.page,
        limit: params?.limit,
      });
      return request<Post[]>(`/posts${qs}`);
    },

    async getPost(postId: string): Promise<Post> {
      if (isDemoMode()) {
        const found = ensureDemo().posts.find((p) => p.id === postId);
        if (!found) throw new ApiError('NOT_FOUND', 'Post not found.', 404);
        return found;
      }
      return request<Post>(`/posts/${postId}`);
    },

    async generateDraftsForPost(
      postId: string,
      payload: DraftGenerateRequest = {}
    ): Promise<DraftSummary[]> {
      if (isDemoMode()) {
        const store = ensureDemo();
        const post = store.posts.find((p) => p.id === postId);
        if (!post) throw new ApiError('NOT_FOUND', 'Post not found.', 404);
        const now = new Date().toISOString();
        const newDraft: DraftSummary = {
          id: crypto.randomUUID(),
          user_id: store.profile.id,
          post_id: postId,
          draft_text:
            'Strong point here—especially the emphasis on reliability over ad-hoc workarounds. Have you shared benchmarks on this setup?',
          edited_text: null,
          style_variant: payload.tone || 'concise-observation',
          relevance_score: 0.89,
          quality_score: 0.87,
          status: 'pending',
          generation_model: 'offline-preview',
          generation_metadata: { regenerated: false },
          created_at: now,
          updated_at: now,
        };
        post.drafts = [newDraft, ...post.drafts];
        post.status = 'drafted';
        store.drafts = [{ ...newDraft, post: { ...post, drafts: [] } }, ...store.drafts];
        return [newDraft];
      }
      return request<DraftSummary[]>(`/posts/${postId}/drafts`, {
        method: 'POST',
        body: JSON.stringify(payload),
      });
    },

    async listDrafts(params?: {
      status?: string;
      platform?: string;
      page?: number;
      limit?: number;
    }): Promise<DraftWithPost[]> {
      if (isDemoMode()) {
        let items = [...ensureDemo().drafts];
        if (params?.status) items = items.filter((d) => d.status === params.status);
        if (params?.platform) items = items.filter((d) => d.post?.platform === params.platform);
        return items;
      }
      const qs = buildQuery({
        status: params?.status,
        platform: params?.platform,
        page: params?.page,
        limit: params?.limit,
      });
      return request<DraftWithPost[]>(`/drafts${qs}`);
    },

    async updateDraft(draftId: string, payload: DraftUpdateRequest): Promise<DraftSummary> {
      if (isDemoMode()) {
        const store = ensureDemo();
        let updated: DraftSummary | null = null;
        store.drafts = store.drafts.map((d) => {
          if (d.id !== draftId) return d;
          const nextStatus = payload.status ?? (payload.edited_text !== undefined ? 'edited' : d.status);
          const next = {
            ...d,
            edited_text: payload.edited_text !== undefined ? payload.edited_text : d.edited_text,
            status: nextStatus,
            updated_at: new Date().toISOString(),
          };
          updated = next;
          return next;
        });
        if (!updated) throw new ApiError('NOT_FOUND', 'Draft not found.', 404);
        return updated;
      }
      return request<DraftSummary>(`/drafts/${draftId}`, {
        method: 'PATCH',
        body: JSON.stringify(payload),
      });
    },

    async regenerateDraft(draftId: string, payload: DraftRegenerateRequest): Promise<DraftSummary> {
      if (isDemoMode()) {
        const store = ensureDemo();
        let updated: DraftSummary | null = null;
        store.drafts = store.drafts.map((d) => {
          if (d.id !== draftId) return d;
          const note = payload.instruction ? ` (${payload.instruction})` : '';
          const next: DraftWithPost = {
            ...d,
            draft_text: `Refined ${payload.tone ?? 'conversational'} ${payload.length ?? 'short'} comment${note}: This aligns closely with what we've seen in production workflows—especially keeping humans in the loop before anything goes live.`,
            edited_text: null,
            status: 'pending',
            updated_at: new Date().toISOString(),
          };
          updated = next;
          return next;
        });
        if (!updated) throw new ApiError('NOT_FOUND', 'Draft not found.', 404);
        return updated;
      }
      return request<DraftSummary>(`/drafts/${draftId}/regenerate`, {
        method: 'POST',
        body: JSON.stringify(payload),
      });
    },

    async markDraft(draftId: string, action: DraftAction): Promise<DraftSummary> {
      if (isDemoMode()) {
        const store = ensureDemo();
        let updated: DraftSummary | null = null;
        store.drafts = store.drafts.map((d) => {
          if (d.id !== draftId) return d;
          const next = { ...d, status: action, updated_at: new Date().toISOString() };
          updated = next;
          return next;
        });
        if (!updated) throw new ApiError('NOT_FOUND', 'Draft not found.', 404);
        return updated;
      }
      return request<DraftSummary>(`/drafts/${draftId}/mark`, {
        method: 'POST',
        body: JSON.stringify({ action }),
      });
    },

    async deleteDraft(draftId: string): Promise<void> {
      if (isDemoMode()) {
        const store = ensureDemo();
        store.drafts = store.drafts.filter((d) => d.id !== draftId);
        return;
      }
      return request<void>(`/drafts/${draftId}`, { method: 'DELETE' });
    },

    async getPreferences(): Promise<Preferences> {
      if (isDemoMode()) {
        return { ...ensureDemo().preferences };
      }
      return request<Preferences>('/preferences');
    },

    async updatePreferences(payload: PreferencesUpdateRequest): Promise<Preferences> {
      if (isDemoMode()) {
        const store = ensureDemo();
        store.preferences = {
          ...store.preferences,
          ...payload,
          updated_at: new Date().toISOString(),
        };
        return { ...store.preferences };
      }
      return request<Preferences>('/preferences', {
        method: 'PUT',
        body: JSON.stringify(payload),
      });
    },

    async listStyleSamples(): Promise<StyleSample[]> {
      if (isDemoMode()) {
        return [...ensureDemo().styleSamples];
      }
      return request<StyleSample[]>('/style-samples');
    },

    async createStyleSample(sampleText: string): Promise<StyleSample> {
      if (isDemoMode()) {
        const store = ensureDemo();
        const item: StyleSample = {
          id: crypto.randomUUID(),
          user_id: store.profile.id,
          sample_text: sampleText.trim(),
          created_at: new Date().toISOString(),
        };
        store.styleSamples = [item, ...store.styleSamples];
        return item;
      }
      return request<StyleSample>('/style-samples', {
        method: 'POST',
        body: JSON.stringify({ sample_text: sampleText }),
      });
    },

    async deleteStyleSample(sampleId: string): Promise<void> {
      if (isDemoMode()) {
        const store = ensureDemo();
        store.styleSamples = store.styleSamples.filter((s) => s.id !== sampleId);
        return;
      }
      return request<void>(`/style-samples/${sampleId}`, { method: 'DELETE' });
    },

    async getNotificationSettings(): Promise<NotificationSettings> {
      if (isDemoMode()) {
        return { ...ensureDemo().notifications };
      }
      return request<NotificationSettings>('/notifications/settings');
    },

    async updateNotificationSettings(
      payload: NotificationSettingsUpdateRequest
    ): Promise<NotificationSettings> {
      if (isDemoMode()) {
        const store = ensureDemo();
        store.notifications = {
          ...store.notifications,
          ...payload,
          updated_at: new Date().toISOString(),
        };
        return { ...store.notifications };
      }
      return request<NotificationSettings>('/notifications/settings', {
        method: 'PUT',
        body: JSON.stringify(payload),
      });
    },

    async connectTelegram(): Promise<TelegramConnectResponse> {
      if (isDemoMode()) {
        const code = 'SE-DEMO-482910';
        return {
          verification_code: code,
          expires_at: new Date(Date.now() + 15 * 60_000).toISOString(),
          bot_username: 'SocialEngagePreviewBot',
          deep_link_url: `https://t.me/SocialEngagePreviewBot?start=${code}`,
          instructions: `Open the bot link and press Start, or verify code '${code}' within 15 minutes.`,
        };
      }
      return request<TelegramConnectResponse>('/notifications/telegram/connect', {
        method: 'POST',
      });
    },

    async verifyTelegram(payload: TelegramVerifyRequest): Promise<NotificationSettings> {
      if (isDemoMode()) {
        const store = ensureDemo();
        store.notifications = {
          ...store.notifications,
          telegram_connected: true,
          telegram_enabled: true,
          telegram_chat_id_masked: `***${payload.chat_id.slice(-4)}`,
          updated_at: new Date().toISOString(),
        };
        return { ...store.notifications };
      }
      return request<NotificationSettings>('/notifications/telegram/verify', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
    },

    async disconnectTelegram(): Promise<NotificationSettings> {
      if (isDemoMode()) {
        const store = ensureDemo();
        store.notifications = {
          ...store.notifications,
          telegram_connected: false,
          telegram_enabled: false,
          telegram_chat_id_masked: null,
          updated_at: new Date().toISOString(),
        };
        return { ...store.notifications };
      }
      return request<NotificationSettings>('/notifications/telegram/disconnect', {
        method: 'POST',
      });
    },

    async sendTestNotification(): Promise<{ delivered: boolean; mode: string; detail: string }> {
      if (isDemoMode()) {
        return {
          delivered: true,
          mode: 'offline-preview',
          detail: 'Simulated test message delivered in Offline Demo Preview.',
        };
      }
      return request('/notifications/test', { method: 'POST' });
    },
  };
}

export type ApiClient = ReturnType<typeof createApiClient>;
