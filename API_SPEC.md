# API Specification
## REST API v1

Base path: `/api/v1`  
Authentication: Supabase JWT bearer token for user endpoints. Worker endpoints use a separate server secret or signed job token.

## Targets
### `GET /targets`
List the authenticated user's targets. Query: `platform`, `status`, `page`, `limit`.

### `POST /targets`
Request:
```json
{
  "platform": "linkedin",
  "profile_url": "https://www.linkedin.com/in/example/",
  "display_name": "Example",
  "source_type": "manual"
}
```
Response: target object and source capability status.

### `PATCH /targets/{target_id}`
Update display name, preferences, or status.

### `DELETE /targets/{target_id}`
Delete target and related target-post associations.

## Posts
### `POST /posts/ingest-manual`
Request:
```json
{
  "platform": "linkedin",
  "post_url": "https://www.linkedin.com/posts/example"
}
```
Validate URL and ownership. Do not scrape restricted content; allow user to provide text/preview when source cannot be accessed.

### `GET /posts`
List detected posts with filters: `platform`, `target_id`, `status`, `since`.

### `GET /posts/{post_id}`
Return post summary, source, and associated drafts.

## Drafts
### `POST /posts/{post_id}/drafts`
Request:
```json
{
  "variants": 2,
  "tone": "professional-conversational",
  "length": "short"
}
```
Response: generated draft objects. Apply rate limits and user quota.

### `GET /drafts`
List drafts. Query: `status`, `platform`, `page`, `limit`.

### `PATCH /drafts/{draft_id}`
Request:
```json
{
  "edited_text": "Updated comment text",
  "status": "edited"
}
```

### `POST /drafts/{draft_id}/regenerate`
Request:
```json
{
  "tone": "thoughtful",
  "instruction": "Make it more specific and less formal"
}
```

### `POST /drafts/{draft_id}/mark`
Request:
```json
{
  "action": "copied"
}
```
Allowed actions: `copied`, `opened`, `skipped`, `archived`. No publishing action unless an approved official integration explicitly supports it.

## Preferences
### `GET /preferences`
### `PUT /preferences`
Update tone, length, language, relevance threshold, topics, and excluded phrases.

## Notifications
### `POST /notifications/telegram/connect`
Create a secure connect flow using bot deep link or one-time code. Never accept arbitrary chat IDs without verification.

### `POST /notifications/test`
Send a test message to the verified chat.

## Worker endpoints
- `POST /internal/jobs/monitor`
- `POST /internal/jobs/process-post`
- `POST /internal/jobs/daily-digest`

Protect all internal endpoints with signed authorization. Validate payloads and make jobs idempotent.

## Standard errors
```json
{
  "error": {
    "code": "SOURCE_UNAVAILABLE",
    "message": "This source is not currently supported for automated monitoring.",
    "request_id": "uuid"
  }
}
```
Use appropriate HTTP codes: 400 validation, 401 unauthenticated, 403 unauthorized, 404 missing, 409 conflict, 429 rate limit, 500 internal error.
