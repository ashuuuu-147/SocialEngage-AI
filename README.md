# SocialEngage AI — Project Documentation & Developer Guide

A cloud-first AI social engagement assistant that monitors authorized sources for posts from user-selected profiles, generates context-aware comment drafts, and sends them for human review.

> **Tagline:** *"Meaningful engagement, made easier."*

---

## Documentation Map
- `PRD.md` — product requirements, scope, users, features, acceptance criteria
- `design.md` — UI/UX direction, screens, design tokens, interaction rules
- `ARCHITECTURE.md` — system architecture, services, deployment approach
- `DATABASE_SCHEMA.md` — PostgreSQL/Supabase schema and constraints
- `API_SPEC.md` — REST API endpoints and request/response contracts
- `AI_COMMENT_ENGINE.md` — prompt design, quality rules, personalization
- `MONITORING_WORKFLOW.md` — source adapters, scheduled processing, deduplication
- `SECURITY_COMPLIANCE.md` — privacy, secrets, platform rules, safety boundaries
- `ROADMAP.md` — milestones, build order, testing and acceptance
- `IMPLEMENTATION_PLAN.md` — resolved architecture, dependencies, and test strategy
- `AGENT_TASKS.md` — multi-agent task allocation and completion report
- `PROJECT_STATUS.md` — MVP readiness, feature status table, and known limitations

---

## Product Guardrails
1. Use permitted, authorized data sources only.
2. Do not automate unauthorized posting or bypass platform protections.
3. Human approval is required before publishing (there is no auto-post action).
4. Never request or store social-media passwords or browser session cookies.
5. Design cloud jobs to operate when the user's laptop is off.
6. Provide a manual URL/import workflow when platform APIs do not allow profile monitoring.
7. Keep free-tier use configurable; never promise unlimited free operation.

---

## Repository Structure

```text
apps/web/                 # React + TypeScript + Vite dashboard
services/api/             # Python + FastAPI backend, AI engine, adapters, workers
infra/migrations/         # Supabase PostgreSQL SQL migrations + RLS policies
infra/scheduled-jobs/     # Cloudflare Worker Cron & GitHub Actions cloud triggers
.env.example              # Documented environment variable placeholders (no secrets)
```

---

## Local Setup & Development

### 1. Environment Variables
Copy `.env.example` to `.env` in the repository root (and optionally `apps/web/.env`):
- For local testing without live external credentials, keep `DEV_AUTH_BYPASS=true`, `AI_PROVIDER=mock`, `ENABLE_MOCK_SOURCES=true`, and `DATABASE_URL=sqlite:///./socialengage_local.db`.
- For production or live integrations, configure `DATABASE_URL` (Supabase PostgreSQL), `SUPABASE_JWT_SECRET`, `GEMINI_API_KEY` (with `AI_PROVIDER=gemini`), `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_USERNAME`, and a strong `INTERNAL_JOB_SECRET`.

### 2. Backend API (`services/api`)
```powershell
cd "services/api"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
- Interactive OpenAPI / Swagger UI: `http://localhost:8000/docs`
- Health endpoint: `http://localhost:8000/health`

### 3. Frontend Web App (`apps/web`)
```powershell
cd "apps/web"
npm install
npm run dev
```
- Web dashboard: `http://localhost:5173` (Vite proxies `/api/*` to `http://localhost:8000`).

---

## Testing Instructions

### Backend Tests & Linting
```powershell
cd "services/api"
.\.venv\Scripts\ruff check app tests --select F,E9,B023
.\.venv\Scripts\pytest -v
```

### Frontend Typecheck, Tests & Production Build
```powershell
cd "apps/web"
npm run lint
npm test
npm run build
```

---

## API Overview (`/api/v1`)
All user endpoints require a Supabase JWT (`Authorization: Bearer <token>`) in production (or `X-Dev-User-Id` when `DEV_AUTH_BYPASS=true` in non-production). Errors follow `{ "error": { "code", "message", "request_id" } }`.

- **Overview & Activity:** `GET /overview`, `GET /activity`, `GET /monitoring/jobs`
- **Watchlist Targets:** `GET /sources/capabilities`, `GET /targets`, `POST /targets`, `PATCH /targets/{id}`, `DELETE /targets/{id}`, `POST /targets/{id}/check`
- **Posts & Intake:** `POST /posts/ingest-manual`, `POST /posts/import-notifications`, `GET /posts`, `GET /posts/{id}`, `POST /posts/{id}/drafts`
- **Draft Review:** `GET /drafts`, `PATCH /drafts/{id}`, `POST /drafts/{id}/regenerate`, `POST /drafts/{id}/mark` (`copied|opened|skipped|archived`), `DELETE /drafts/{id}`
- **Preferences & Style:** `GET /preferences`, `PUT /preferences`, `GET /style-samples`, `POST /style-samples`, `DELETE /style-samples/{id}`
- **Notifications:** `GET /notifications/settings`, `PUT /notifications/settings`, `POST /notifications/telegram/connect`, `POST /notifications/telegram/verify`, `POST /notifications/telegram/webhook`, `POST /notifications/telegram/disconnect`, `POST /notifications/test`
- **Profile & Data Rights:** `GET /profile`, `PATCH /profile`, `GET /account/export`, `DELETE /account`
- **Cloud Worker Endpoints (HMAC / Secret Signed):** `POST /internal/jobs/monitor`, `POST /internal/jobs/process-post`, `POST /internal/jobs/daily-digest`

---

## Cloud Deployment Guide

Run the production preflight validator first (after exporting production env vars):
```powershell
cd "services/api"
.\.venv\Scripts\python scripts/check_production_env.py
```

1. **Database & Auth (Supabase):**
   - Create a Supabase project.
   - Apply SQL migrations in order via Supabase SQL Editor or `psql`:
     1. `infra/migrations/001_initial_schema.sql`
     2. `infra/migrations/002_rls_policies.sql`
     3. `infra/migrations/003_indexes_and_triggers.sql`
   - Copy `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_JWT_SECRET`, and PostgreSQL `DATABASE_URL`. (Backend verifies both HS256 secrets and Supabase JWKS RS256/ES256 tokens.)
2. **Backend API (`services/api`):**
   - Ready-to-deploy configs included:
     - **Google Cloud Run:** `.\infra\deploy\cloudrun-deploy.ps1 -ProjectId "<YOUR_PROJECT>" -Region "asia-south1"`
     - **Render:** `render.yaml` Blueprint
     - **Docker:** `services/api/Dockerfile`
   - Set `APP_ENV=production`, `DEV_AUTH_BYPASS=false`, `ENABLE_MOCK_SOURCES=false`, `CORS_ORIGINS=https://your-web-domain`, `INTERNAL_JOB_SECRET`, `AI_PROVIDER=gemini`, `GEMINI_API_KEY`, and optional `TELEGRAM_BOT_TOKEN` + `TELEGRAM_WEBHOOK_SECRET`.
   - Register `POST https://your-api-domain/api/v1/notifications/telegram/webhook` with `secret_token=TELEGRAM_WEBHOOK_SECRET` via Telegram `setWebhook` for automatic `/start <code>` linking.
3. **Frontend (`apps/web`):**
   - Ready-to-deploy configs included: `apps/web/vercel.json` (Vercel), `apps/web/Dockerfile` + `nginx.conf` (container/Cloudflare Pages static build).
   - Set `VITE_API_BASE_URL=https://your-api-domain/api/v1`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, and `VITE_DEV_AUTH_BYPASS=false` (enables Email/Password & Magic Link Supabase Auth UI and hides dev bypass).
4. **Cloud Scheduler (`infra/scheduled-jobs/`):**
   - Option A (Cloudflare Workers Cron): Deploy `infra/scheduled-jobs/cloudflare-worker.js` with `wrangler deploy` and set secrets `API_BASE_URL` and `INTERNAL_JOB_SECRET`.
   - Option B (GitHub Actions): Configure repository secrets `API_BASE_URL` and `INTERNAL_JOB_SECRET` and enable `infra/scheduled-jobs/github-actions-cron.yml`.
