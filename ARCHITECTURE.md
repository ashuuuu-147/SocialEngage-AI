# Technical Architecture
## SocialEngage AI

## 1. Architecture overview
Use a modular, cloud-first architecture:

- Web client: React + TypeScript + Vite
- API: Python + FastAPI
- Database/auth: Supabase PostgreSQL + Supabase Auth
- Scheduler: Cloudflare Workers Cron or another free-tier scheduled service
- Queue: database-backed job queue for MVP; managed queue later if needed
- AI: provider adapter (Gemini or configurable provider)
- Notifications: Telegram Bot API
- Hosting: frontend on Vercel/Cloudflare Pages; API on a suitable free-tier host or Workers-compatible service

Do not assume any provider's free tier is permanent or unlimited.

## 2. High-level flow
1. Scheduler triggers source checks.
2. Source adapter retrieves permitted data.
3. Normalize and validate post.
4. Deduplication checks unique source key.
5. Save post and enqueue analysis.
6. Relevance engine filters post.
7. AI adapter generates draft(s).
8. Quality checks validate draft.
9. Save drafts.
10. Telegram notifier sends notification.
11. User reviews in web app and copies/opens the post for manual publication.

## 3. Modules
- `auth`: user identity and access.
- `targets`: tracked profiles.
- `sources`: authorized source adapters.
- `monitoring`: scheduled checks and job orchestration.
- `posts`: normalization and deduplication.
- `relevance`: rules and score.
- `ai`: provider abstraction and prompt templates.
- `drafts`: create/edit/regenerate/review.
- `notifications`: Telegram and digest.
- `activity`: audit trail.
- `settings`: user preferences and retention.

## 4. Suggested repository structure
```text
socialengage-ai/
  apps/
    web/
      src/
        components/
        pages/
        hooks/
        lib/
        styles/
  services/
    api/
      app/
        routers/
        services/
        models/
        schemas/
        source_adapters/
        ai/
        workers/
        core/
      tests/
  infra/
    migrations/
    scheduled-jobs/
  docs/
    PRD.md
    design.md
    ARCHITECTURE.md
    DATABASE_SCHEMA.md
    API_SPEC.md
    AI_COMMENT_ENGINE.md
    MONITORING_WORKFLOW.md
    SECURITY_COMPLIANCE.md
    ROADMAP.md
  .env.example
  README.md
```

## 5. Source adapter interface
Every adapter must implement:
- `validate_target(url)`
- `check_access()`
- `fetch_recent_posts(target, cursor)`
- `normalize_post(raw)`
- `health_check()`

Adapter must document its authorization model, data limits, and platform restrictions. If access is not available, return a clear unsupported status and offer manual URL intake.

## 6. Reliability
- Use idempotent jobs.
- Apply bounded retries with exponential backoff.
- Respect source rate limits.
- Track `last_checked_at`, `last_success_at`, and `last_error`.
- Use timeouts on network/API calls.
- Store job status and error codes.
- Avoid processing stale posts beyond configured lookback.

## 7. Deployment
Separate:
- Frontend deployment.
- API deployment.
- Scheduled worker.
- Database and auth.
- Secrets configuration.

Scheduled tasks must run in the cloud and must not rely on an open browser or laptop.

## 8. Observability
Log:
- job ID
- source adapter
- target ID
- processing stage
- duration
- outcome
- sanitized error code

Never log tokens, secrets, private message content, or unnecessary personal data.
