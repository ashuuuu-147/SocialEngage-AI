# Development Roadmap

## Milestone 0 — Repository setup
- Create monorepo or clean frontend/backend split.
- Add formatting, linting, environment examples.
- Add README and docs.
- Confirm local dev commands.

## Milestone 1 — UI foundation
- Build responsive app shell.
- Implement Overview, Watchlist, Inbox, Drafts, Activity, Settings.
- Use mock data only for initial UI development; label it clearly.
- Add loading, empty, and error states.

## Milestone 2 — Authentication and database
- Configure Supabase Auth.
- Create migrations.
- Enable and test RLS.
- Implement target and preference CRUD.

## Milestone 3 — Manual post intake
- Accept user-provided post URL and optional text.
- Validate platform and canonical URL.
- Save post with deduplication.
- Add post detail view.

## Milestone 4 — AI drafts
- Implement AI provider abstraction.
- Add structured prompt and JSON validation.
- Generate drafts and quality scores.
- Add edit, regenerate, copy, open, skip.

## Milestone 5 — Telegram
- Implement bot connection flow.
- Verify user/chat association.
- Send draft notifications.
- Add test notification and disconnect.

## Milestone 6 — Cloud monitoring
- Implement scheduler and job records.
- Add one authorized source adapter.
- Add source health, rate limits, retries, and logs.
- Clearly mark unsupported targets.

## Milestone 7 — QA and deployment
- Unit and integration tests.
- RLS tests.
- API validation tests.
- AI quality test set.
- Deploy frontend, API, scheduler, and database.
- Verify jobs run with laptop off.

## Definition of done
- All MVP acceptance criteria in PRD pass.
- No secrets in source control.
- No unauthorized publishing flow.
- Errors and unsupported integrations are clearly surfaced.
- Deployment and setup instructions are documented.
