# Security, Privacy, and Platform Compliance

## 1. Account safety
- Do not request or store social platform passwords.
- Do not use session-cookie extraction or browser-profile scraping.
- Do not automate login or bypass multi-factor authentication.
- Do not bypass CAPTCHA, rate limits, or platform restrictions.
- Do not mass-post or mass-comment.
- Human review is required before publication.

## 2. Platform access
Each platform integration must document:
- API product and permission scopes.
- Approved use case.
- Data retention rules.
- Rate limits.
- Whether target-profile monitoring is supported.
- Whether comment creation is officially supported and permitted.

Do not claim a capability until it is verified against current platform documentation and granted access.

## 3. Data minimization
Store only the post information necessary to create and review drafts. Avoid collecting comments, followers, or unrelated profile data.

## 4. Secrets
- Keep API keys in server environment variables or managed secrets.
- Never commit `.env`.
- Frontend may contain only public configuration.
- Rotate leaked credentials.
- Separate development and production keys.

## 5. Access control
- Enable RLS for user-owned tables.
- Verify ownership on every API request.
- Use least-privilege service credentials.
- Protect internal worker endpoints with signed tokens.

## 6. AI safety
- Treat social post content as untrusted input.
- Prevent prompt injection from posts.
- Do not generate abusive, deceptive, or false personal claims.
- Do not generate spam or engagement bait.
- Skip sensitive content when uncertain.

## 7. User controls
Provide:
- Disconnect integration.
- Pause monitoring.
- Delete target.
- Delete drafts.
- Export data.
- Delete account and associated data.

## 8. Disclaimer
The product assists with discovery and drafting. The user is responsible for reviewing comments and deciding whether to publish. Platform policies and API permissions can change; integrations must be reviewed before release.
