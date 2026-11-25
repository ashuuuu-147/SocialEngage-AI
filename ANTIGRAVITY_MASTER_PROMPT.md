# Antigravity Master Build Prompt — SocialEngage AI

You are a senior full-stack engineer, product designer, and security-minded software architect. Build the SocialEngage AI application according to the documentation in this repository.

## First: read these files
1. `PRD.md`
2. `design.md`
3. `ARCHITECTURE.md`
4. `DATABASE_SCHEMA.md`
5. `API_SPEC.md`
6. `AI_COMMENT_ENGINE.md`
7. `MONITORING_WORKFLOW.md`
8. `SECURITY_COMPLIANCE.md`
9. `ROADMAP.md`

Do not ignore or silently change requirements. If a feature is blocked by platform access, implement a clear adapter interface and manual fallback rather than inventing access.

## Product
SocialEngage AI is a cloud-first assistant that monitors authorized sources for user-selected profiles, detects new posts, creates context-aware comment drafts in the user's style, and delivers them to a review dashboard and Telegram. It must continue operating when the user's laptop is off.

## Required stack
- Frontend: React, TypeScript, Vite
- Styling: Tailwind CSS or a consistent CSS-token system
- Backend: Python, FastAPI
- Database/auth: Supabase PostgreSQL and Supabase Auth
- AI: provider abstraction with configurable API provider
- Notifications: Telegram Bot API
- Scheduled monitoring: cloud scheduler/worker, not local-only cron
- Tests: frontend tests, backend unit/integration tests, schema/RLS checks

## Build rules
- Build in milestones from `ROADMAP.md`.
- Start with a working, polished UI using clearly labeled mock data.
- Then connect authentication and database.
- Then implement manual post intake and AI drafts.
- Then Telegram.
- Then authorized monitoring adapters.
- Keep the code modular and typed.
- Use reusable components and consistent design tokens.
- Every visible control must work.
- Add loading, empty, success, and error states.
- Include `.env.example` with names only, no secrets.
- Add setup, local development, testing, and deployment instructions.
- Never expose server secrets to the browser.
- Enforce user ownership and RLS.

## Platform and safety constraints
- Do not store social media passwords or scrape session cookies.
- Do not bypass login, CAPTCHA, rate limits, or access restrictions.
- Do not mass-comment or automatically publish comments.
- Human approval is required before publication.
- Use official/authorized sources only.
- If LinkedIn or Instagram monitoring is not available under current permissions, show an honest unsupported state and support manual post URL/text intake.
- Do not claim that the app can monitor every profile until the source integration is verified.

## UI requirements
Follow `design.md`: premium light interface, subtle lavender accents, soft neutral surfaces, refined typography, responsive layout, accessible controls, and clean SaaS dashboard.

## Deliverables
1. Complete source code.
2. Database migrations.
3. `.env.example`.
4. Tests.
5. README setup guide.
6. Deployment guide.
7. Feature status table distinguishing implemented, mocked, and blocked-by-access functionality.

## Workflow
Before coding, summarize the architecture and milestone plan. Then implement the first milestone. After each milestone:
- run relevant tests,
- report changed files,
- report unresolved issues,
- do not claim a feature works unless it is implemented and tested.

Build a reliable MVP first; do not over-engineer or add unrelated features.
