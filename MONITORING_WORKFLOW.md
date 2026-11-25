# Monitoring and Automation Workflow

## 1. Goal
Run scheduled post checks in the cloud and create drafts only for newly discovered, relevant posts.

## 2. Source hierarchy
Use, in order of preference:
1. Official APIs with granted permissions.
2. Authorized platform integrations.
3. User-authorized feeds or notifications.
4. User-submitted post URLs and text.
5. Manual capture through a browser extension, if implemented.

Do not build source adapters that evade login, access controls, rate limits, or platform restrictions. A source may be unavailable for arbitrary profile monitoring; communicate that clearly.

## 3. Scheduled job
Default interval: 30 minutes, configurable within source limits.

Pseudo-flow:
```text
scheduled_trigger
  -> load active targets
  -> group targets by source adapter
  -> check source health and limits
  -> fetch permitted recent posts
  -> normalize each post
  -> validate URL and metadata
  -> deduplicate
  -> persist post + target association
  -> enqueue post analysis
  -> update target check status
```

## 4. Post processing
```text
new_post
  -> validate content and source
  -> apply user exclusions
  -> relevance analysis
  -> if below threshold: mark skipped
  -> otherwise generate draft variants
  -> quality and repetition checks
  -> save draft
  -> notify user
```

## 5. Job states
`queued`, `running`, `success`, `partial`, `failed`.

Post states:
`discovered`, `analyzing`, `drafted`, `skipped`, `error`.

Draft states:
`pending`, `edited`, `copied`, `opened`, `skipped`, `archived`.

## 6. Idempotency
Use a stable idempotency key based on source/platform post identifier. A retry must not create a second post or duplicate notification unless the previous attempt failed before delivery.

## 7. Backoff and quotas
- Respect source-specific rate limits.
- Retry 429 and transient 5xx with exponential backoff and jitter.
- Do not retry permanent permission errors indefinitely.
- Add per-user and per-provider AI quotas.
- Pause jobs when quota is exhausted and notify user.

## 8. Notifications
Send only after a draft is persisted. Include:
- author and platform
- concise preview
- draft text
- post URL
- dashboard link

Do not include access tokens or sensitive source payloads.

## 9. Laptop independence
The scheduler, database, AI processing, and Telegram delivery must run on cloud infrastructure. The local browser extension, if present, is only for user-assisted capture and is not the core scheduler.
