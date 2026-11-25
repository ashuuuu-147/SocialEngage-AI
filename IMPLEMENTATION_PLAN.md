# SocialEngage AI — Implementation Plan

**Version:** 1.0  
**Lead Architect:** Agent 1  
**Target:** MVP Production-Ready Cloud-First Social Engagement Assistant  

---

## 1. Documentation Synthesis & Product Vision

SocialEngage AI is a cloud-first web application that helps professionals, creators, founders, and developers stay engaged with selected people and pages on **LinkedIn** and **Instagram** (subject to authorized data access). The core pipeline is:

**Monitor -> Analyze -> Draft -> Notify -> Human Review (Copy & Open)**

### Non-Negotiable Guardrails
- **Cloud-first:** Scheduled monitoring, post processing, AI drafting, and Telegram notifications run in the cloud and never depend on the user's laptop staying on.
- **Authorized sources only:** Never request or store social passwords, scrape session cookies, bypass logins/CAPTCHAs, or evade rate limits.
- **Honest platform limitations:** LinkedIn and Instagram restrict arbitrary profile monitoring via public APIs. Where automated monitoring is not granted, targets clearly display an `unsupported` or manual state and route users to **Manual Post URL/Text Intake** or **Authorized Feeds/Notification Imports**.
- **Human-in-the-loop:** Never auto-publish comments or display an "Auto-post" action. Users review, edit, regenerate, copy, and open posts manually.
- **User data isolation & secret safety:** Row-Level Security (RLS) in PostgreSQL, server-side ownership checks on every endpoint, secrets strictly in server environment variables, never exposed to Vite client bundles.

---

## 2. Identified Documentation Gaps, Risks & Architectural Resolutions

| Area | Gap / Risk Identified | Architectural Resolution |
| --- | --- | --- |
| **Manual Post Ownership (`posts` table)** | `DATABASE_SCHEMA.md` defines `posts` without a `user_id` column (linked via `target_posts`), whereas `API_SPEC.md` supports `POST /posts/ingest-manual` with only `platform` and `post_url` (no mandatory `target_id`). | Add nullable `submitted_by_user_id uuid references profiles(id) on delete set null` on `posts` so standalone manual posts remain strictly isolated per user under both RLS and API queries. |
| **Deduplication Key (`posts` table)** | `DATABASE_SCHEMA.md` notes unique `(platform, source_post_id)` when ID exists, otherwise `(platform, canonical_url)`. | Add a deterministic `dedupe_key text not null` column computed as `"{platform}:id:{source_post_id}"` or `"{platform}:url:{canonical_url}"` with a unique index, plus `status` (`discovered`, `analyzing`, `drafted`, `skipped`, `error`) from `MONITORING_WORKFLOW.md`. |
| **Extended REST Endpoints** | `API_SPEC.md` specifies core `/targets`, `/posts`, `/drafts`, `/preferences`, `/notifications`, `/internal/jobs/*`, while `PRD.md`, `design.md`, and `SECURITY_COMPLIANCE.md` also require style samples, activity logs, overview metrics, data export, account deletion, and Telegram disconnect/status. | Implement all `API_SPEC.md` endpoints verbatim plus `/overview`, `/style-samples`, `/activity`, `/notifications/settings`, `/notifications/telegram/disconnect`, `/notifications/telegram/verify`, `/account/export`, and `/account` (`DELETE`) under `/api/v1`. |
| **Local Dev & Test Execution without Live Supabase** | Automated CI/local testing needs to run without live Supabase, Gemini, or Telegram credentials. | Provide clean PostgreSQL/Supabase SQL migrations in `infra/migrations/` with full RLS, while supporting SQLAlchemy (`DATABASE_URL` = PostgreSQL in prod, SQLite for local dev/pytest) and a clearly labeled `DEV_AUTH_BYPASS` (disabled by default in production) + `MockAIProvider` + `MockTelegramTransport` + `ENABLE_MOCK_SOURCES` toggle. |
| **SSRF Risk in Authorized Feed Adapter** | Fetching user-supplied feed URLs or post URLs could expose internal network endpoints if unvalidated. | Enforce strict URL validation (`https`/`http` only), DNS/IP private-range blocking (RFC1918, loopback, link-local, metadata IPs), timeouts, and response size caps. |
| **Telegram Chat Verification** | `API_SPEC.md` forbids accepting arbitrary `telegram_chat_id` without verification. | Implement a one-time cryptographic connect token stored server-side (`telegram_link_tokens` or signed token with expiry) paired with a bot deep link `https://t.me/<bot>?start=<token>` and verification endpoint/webhook. |

---

## 3. Repository Structure

```text
SocialEngage AI/
  apps/
    web/                        # React + TypeScript + Vite frontend
      src/
        components/             # Reusable UI components (AppShell, Sidebar, MetricCard, etc.)
        pages/                  # Overview, Watchlist, Inbox, Drafts, Activity, Settings, Auth
        hooks/                  # React Query / API hooks
        lib/                    # Typed API client, auth context, formatters
        styles/                 # CSS design tokens & global styles
  services/
    api/                        # Python + FastAPI backend
      app/
        core/                   # Config, security/JWT, logging, rate limiting, errors
        db/                     # SQLAlchemy session & base
        models/                 # ORM models matching DATABASE_SCHEMA.md
        schemas/                # Pydantic request/response contracts
        routers/                # v1 API routers + internal job routers
        services/               # Business logic (targets, posts, drafts, preferences, activity, account)
        ai/                     # Provider abstraction, prompts, validator, quality & repetition scorer
        source_adapters/        # Base interface + official_api, authorized_feed, notification_import, manual
        notifications/          # Telegram Bot API client & digest formatter
        workers/                # Monitoring runner, post processor, backoff/quota manager
      tests/                    # Unit, API contract, isolation, AI quality, and migration checks
  infra/
    migrations/                 # Supabase PostgreSQL SQL migrations + RLS policies
    scheduled-jobs/             # Cloudflare Worker Cron + GitHub Actions cloud scheduler
  docs/                         # Reference copies / links to root specification docs
  .env.example                  # Documented environment variable placeholders (no secrets)
  README.md                     # Updated setup, dev, testing, and deployment guide
  IMPLEMENTATION_PLAN.md        # This plan
  AGENT_TASKS.md                # Multi-agent task allocation & status
  PROJECT_STATUS.md             # Live status, deliverables, limitations, MVP readiness
```

---

## 4. Development Phases & Dependencies

1. **Phase 1 — Documentation Analysis & Planning** *(Complete upon creation of plan docs)*
   - Read all 11 spec documents; resolve gaps; produce `IMPLEMENTATION_PLAN.md`, `AGENT_TASKS.md`, `PROJECT_STATUS.md`.
2. **Phase 2 — Project Foundation**
   - Create directory structure, `.env.example`, `.gitignore`, Python `pyproject.toml`/`requirements.txt`, Vite/React/TS `package.json`, linting/formatting configs.
3. **Phase 3 — Database & Backend Core** *(Depends on Phase 2)*
   - Author Supabase SQL migrations (`001_schema.sql`, `002_rls.sql`, `003_functions.sql`).
   - Implement FastAPI core, Supabase JWT + dev auth, ORM models, Pydantic schemas, and CRUD routers (`targets`, `posts`, `drafts`, `preferences`, `style_samples`, `activity`, `overview`, `account`).
4. **Phase 4 — AI Comment Engine** *(Depends on Phase 3 schemas/models)*
   - Implement `AIProvider` (`GeminiProvider`, `OpenAICompatibleProvider`, `MockAIProvider`).
   - Implement untrusted-input prompt wrapper, structured JSON parser with single retry, quality scorer (6 weighted criteria), repetition detector, and relevance/exclusion filter.
5. **Phase 5 — Monitoring & Notifications** *(Depends on Phase 3 & 4)*
   - Implement `SourceAdapter` interface and adapters (`ManualAdapter`, `AuthorizedFeedAdapter`, `NotificationImportAdapter`, `OfficialAPIAdapter` with honest access status).
   - Implement idempotent worker jobs (`monitor`, `process-post`, `daily-digest`), exponential backoff with jitter, and quota tracking.
   - Implement Telegram Bot connect verification flow, notifications, test trigger, and disconnect.
   - Implement Cloudflare Worker Cron script (`infra/scheduled-jobs/`).
6. **Phase 6 — Frontend Dashboard** *(Depends on Phase 3 API contracts; parallelizable with Phase 4/5)*
   - Implement CSS design token system from `design.md` (light lavender/neutral SaaS aesthetic).
   - Build `AppShell`, `Sidebar`, `Topbar`, reusable components, and all 6 primary pages + Auth/Onboarding + Manual Post Intake modal.
   - Connect all UI controls to real FastAPI endpoints (with optional clearly labeled Demo/Mock mode if backend is offline or user explores demo).
7. **Phase 7 — Integration** *(Depends on Phases 3–6)*
   - Verify end-to-end flows across UI -> FastAPI -> DB -> AI Engine -> Source Adapters -> Telegram -> Activity Logs.
8. **Phase 8 — Testing & Security Verification** *(Depends on Phase 7)*
   - Backend `pytest` suite: API contracts, auth & ownership isolation, deduplication, AI JSON validation & prompt-injection/quality test cases, rate-limit/backoff, SSRF validation, secrets hygiene.
   - Frontend TypeScript build (`tsc --noEmit`, `vite build`) and Vitest component/UI tests.
9. **Phase 9 — MVP Completion**
   - Validate all 10 PRD acceptance criteria, finalize `README.md`, `DEPLOYMENT.md` (or deployment section), and `PROJECT_STATUS.md`.

---

## 5. Testing Strategy

- **Database & RLS Verification:** SQL migration syntax check + automated tests verifying user A cannot read/modify/delete user B's targets, posts, drafts, style samples, notification settings, or activity logs.
- **API Contract Tests (`pytest` + `TestClient`):** Every endpoint in `API_SPEC.md` tested for 200/201, 400 validation errors, 401 unauthenticated, 403/404 ownership isolation, 409 conflicts, and standard `{ "error": { "code", "message", "request_id" } }` format.
- **AI Engine Tests:** Schema validation, malformed output single-retry & safe fallback, prompt-injection resilience, exclusion filtering, repetition penalty, and the 6 test scenarios from `AI_COMMENT_ENGINE.md`.
- **Monitoring & Idempotency Tests:** Duplicate post ingestion prevented by `dedupe_key`; worker retries on transient failures; permanent errors mark target `error` or `unsupported`; internal endpoints reject unsigned requests.
- **Frontend Tests (`vitest` + `@testing-library/react` + `tsc`):** Type-checking, production build, component rendering, empty/error states, and ensuring zero "Auto-post" controls exist.

---

## 6. MVP Completion Criteria

All 10 PRD acceptance criteria verified:
1. User can sign in and manage a watchlist of profiles/pages.
2. User can submit a valid post URL (and optional preview text) manually.
3. Duplicate posts are prevented at database and application level.
4. AI creates up to 3 relevant drafts with quality scores or explains why the post was skipped.
5. Drafts appear in the Review Queue and optionally send to verified Telegram.
6. User can edit, regenerate, copy, open external post, skip, and archive drafts (no auto-post).
7. Cloud scheduler worker triggers monitoring & daily digest independently of user's laptop.
8. User can pause monitoring, disconnect Telegram, and view honest source limitations/errors.
9. User can export and delete their account and associated data.
10. Automated test suite and production builds pass with zero hardcoded secrets.
