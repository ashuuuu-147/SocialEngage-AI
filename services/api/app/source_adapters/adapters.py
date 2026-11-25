"""Authorized source adapters: Manual, Authorized Feed, Notification Import, and Official API."""

from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urlparse

import feedparser
import httpx

from app.core.config import Settings
from app.source_adapters.base import (
    NormalizedPost,
    SourceAdapter,
    SourceAdapterError,
    SourceCapability,
    SourceHealth,
    canonicalize_url,
    compute_content_hash,
    compute_dedupe_key,
    extract_post_id,
    validate_public_http_url,
)

PLATFORM_ALLOWED_HOSTS = {
    "linkedin": ("linkedin.com", "www.linkedin.com"),
    "instagram": ("instagram.com", "www.instagram.com"),
}


def validate_platform_url(platform: str, url: str) -> str:
    canon = canonicalize_url(url)
    host = (urlparse(canon).hostname or "").lower()
    allowed = PLATFORM_ALLOWED_HOSTS.get(platform, ())
    if not any(host == h or host.endswith("." + h) for h in allowed):
        raise SourceAdapterError(
            "PLATFORM_URL_MISMATCH",
            f"URL host '{host}' does not match platform '{platform}'.",
        )
    return canon


class ManualAdapter(SourceAdapter):
    source_type = "manual"

    def validate_target(self, platform: str, profile_url: str) -> str:
        return validate_platform_url(platform, profile_url)

    def check_access(self, platform: str) -> SourceCapability:
        return SourceCapability(
            source_type=self.source_type,
            supported=True,
            reason="Manual post URL and text intake is always available and compliant.",
            documentation_note="User submits permitted post URLs and optional preview text directly.",
            requires_manual_fallback=False,
        )

    async def fetch_recent_posts(
        self,
        *,
        platform: str,
        profile_url: str,
        preferences: dict[str, Any],
        cursor: Optional[str] = None,
    ) -> list[NormalizedPost]:
        # Manual targets do not poll automatically; posts are ingested via /posts/ingest-manual.
        return []

    def normalize_post(self, platform: str, raw: dict[str, Any]) -> NormalizedPost:
        canon = validate_platform_url(platform, raw["post_url"])
        source_post_id = raw.get("source_post_id") or extract_post_id(platform, canon)
        content_text = (raw.get("content_text") or "").strip() or None
        return NormalizedPost(
            platform=platform,
            canonical_url=canon,
            source_post_id=source_post_id,
            dedupe_key=compute_dedupe_key(platform, source_post_id, canon),
            author_name=raw.get("author_name"),
            author_url=raw.get("author_url"),
            content_text=content_text,
            media_type=raw.get("media_type") or "text",
            published_at=raw.get("published_at"),
            content_hash=compute_content_hash(content_text),
            source_metadata={"intake_method": "manual", **(raw.get("source_metadata") or {})},
        )

    async def health_check(self, platform: str) -> SourceHealth:
        return SourceHealth(
            healthy=True,
            status="ready",
            details="Manual post intake endpoint operational.",
        )


class AuthorizedFeedAdapter(SourceAdapter):
    """Fetches user-authorized RSS/Atom/JSON feeds with strict SSRF checks."""

    source_type = "authorized_feed"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def validate_target(self, platform: str, profile_url: str) -> str:
        return validate_platform_url(platform, profile_url)

    def check_access(self, platform: str) -> SourceCapability:
        return SourceCapability(
            source_type=self.source_type,
            supported=True,
            reason="Supported when a user-authorized RSS/Atom feed URL is configured in target preferences.",
            documentation_note="Fetches only explicit feed_url provided by the user; never scrapes platform HTML.",
            requires_manual_fallback=False,
        )

    async def fetch_recent_posts(
        self,
        *,
        platform: str,
        profile_url: str,
        preferences: dict[str, Any],
        cursor: Optional[str] = None,
    ) -> list[NormalizedPost]:
        feed_url = (preferences or {}).get("feed_url")
        if not feed_url:
            if self.settings.enable_mock_sources and preferences.get("use_mock_feed"):
                return [
                    self.normalize_post(
                        platform,
                        {
                            "post_url": f"{profile_url.rstrip('/')}/posts/sample-cloud-sync-1",
                            "author_name": preferences.get("display_name") or "Authorized Feed Creator",
                            "author_url": profile_url,
                            "content_text": "We moved our background workers to cloud cron triggers and cut idle laptop dependency to zero.",
                            "published_at": datetime.now(timezone.utc),
                            "source_metadata": {"mock_source": True},
                        },
                    )
                ]
            raise SourceAdapterError(
                "FEED_URL_MISSING",
                "Target preferences must specify 'feed_url' for authorized_feed monitoring.",
                transient=False,
            )

        safe_feed_url = validate_public_http_url(str(feed_url))
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as client:
                resp = await client.get(safe_feed_url, headers={"User-Agent": "SocialEngageAI/1.0"})
        except httpx.RequestError as exc:
            raise SourceAdapterError("FEED_NETWORK_ERROR", f"Network error fetching feed: {exc}", transient=True) from exc

        if resp.status_code == 429 or resp.status_code >= 500:
            raise SourceAdapterError("FEED_TRANSIENT_HTTP", f"Feed returned HTTP {resp.status_code}.", transient=True)
        if resp.status_code >= 400:
            raise SourceAdapterError("FEED_HTTP_ERROR", f"Feed returned HTTP {resp.status_code}.", transient=False)

        parsed = feedparser.parse(resp.text[:1_000_000])
        posts: list[NormalizedPost] = []
        for entry in parsed.entries[:10]:
            link = entry.get("link")
            if not link:
                continue
            try:
                posts.append(
                    self.normalize_post(
                        platform,
                        {
                            "post_url": link,
                            "source_post_id": entry.get("id") or entry.get("guid"),
                            "author_name": entry.get("author") or preferences.get("display_name"),
                            "author_url": profile_url,
                            "content_text": entry.get("summary") or entry.get("title") or "",
                            "source_metadata": {"feed_url": safe_feed_url},
                        },
                    )
                )
            except SourceAdapterError:
                continue
        return posts

    def normalize_post(self, platform: str, raw: dict[str, Any]) -> NormalizedPost:
        canon = canonicalize_url(raw["post_url"])
        source_post_id = raw.get("source_post_id") or extract_post_id(platform, canon)
        content_text = (raw.get("content_text") or "").strip() or None
        return NormalizedPost(
            platform=platform,
            canonical_url=canon,
            source_post_id=source_post_id,
            dedupe_key=compute_dedupe_key(platform, source_post_id, canon),
            author_name=raw.get("author_name"),
            author_url=raw.get("author_url"),
            content_text=content_text,
            media_type=raw.get("media_type") or "text",
            published_at=raw.get("published_at"),
            content_hash=compute_content_hash(content_text),
            source_metadata={"intake_method": "authorized_feed", **(raw.get("source_metadata") or {})},
        )

    async def health_check(self, platform: str) -> SourceHealth:
        return SourceHealth(
            healthy=True,
            status="ready",
            details="Authorized feed parser ready with SSRF validation.",
        )


class NotificationImportAdapter(SourceAdapter):
    source_type = "notification_import"

    def validate_target(self, platform: str, profile_url: str) -> str:
        return validate_platform_url(platform, profile_url)

    def check_access(self, platform: str) -> SourceCapability:
        return SourceCapability(
            source_type=self.source_type,
            supported=True,
            reason="Supported via user-forwarded notification payloads or structured imports.",
            documentation_note="Accepts user-authorized import events via POST /posts/import-notifications.",
            requires_manual_fallback=False,
        )

    async def fetch_recent_posts(
        self,
        *,
        platform: str,
        profile_url: str,
        preferences: dict[str, Any],
        cursor: Optional[str] = None,
    ) -> list[NormalizedPost]:
        return []

    def normalize_post(self, platform: str, raw: dict[str, Any]) -> NormalizedPost:
        canon = validate_platform_url(platform, raw["post_url"])
        source_post_id = raw.get("source_post_id") or extract_post_id(platform, canon)
        content_text = (raw.get("content_text") or "").strip() or None
        return NormalizedPost(
            platform=platform,
            canonical_url=canon,
            source_post_id=source_post_id,
            dedupe_key=compute_dedupe_key(platform, source_post_id, canon),
            author_name=raw.get("author_name"),
            author_url=raw.get("author_url"),
            content_text=content_text,
            media_type=raw.get("media_type") or "text",
            published_at=raw.get("published_at"),
            content_hash=compute_content_hash(content_text),
            source_metadata={"intake_method": "notification_import", **(raw.get("source_metadata") or {})},
        )

    async def health_check(self, platform: str) -> SourceHealth:
        return SourceHealth(
            healthy=True,
            status="ready",
            details="Notification import intake operational.",
        )


class OfficialAPIAdapter(SourceAdapter):
    """Official LinkedIn/Instagram API adapter with honest access & compliance boundaries."""

    source_type = "official_api"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def validate_target(self, platform: str, profile_url: str) -> str:
        return validate_platform_url(platform, profile_url)

    def _has_credentials(self, platform: str) -> bool:
        if platform == "linkedin":
            return bool(self.settings.linkedin_access_token)
        if platform == "instagram":
            return bool(self.settings.instagram_access_token)
        return False

    def check_access(self, platform: str) -> SourceCapability:
        if platform == "linkedin":
            if self._has_credentials("linkedin"):
                return SourceCapability(
                    source_type=self.source_type,
                    supported=True,
                    reason="LinkedIn API token configured; limited to approved organization/member scopes.",
                    documentation_note="LinkedIn Community Management API does not allow arbitrary third-party personal profile monitoring.",
                    requires_manual_fallback=True,
                )
            return SourceCapability(
                source_type=self.source_type,
                supported=False,
                reason="LinkedIn API access for third-party profile monitoring is not granted. Use Manual URL Intake or Authorized Feed.",
                documentation_note="Requires approved LinkedIn Partner/Community Management scopes; arbitrary scraping is prohibited.",
                requires_manual_fallback=True,
            )

        if self._has_credentials("instagram"):
            return SourceCapability(
                source_type=self.source_type,
                supported=True,
                reason="Instagram Graph API token configured; limited to authorized Business/Creator Discovery scopes.",
                documentation_note="Instagram Graph API Business Discovery only supports authorized Business/Creator accounts.",
                requires_manual_fallback=True,
            )
        return SourceCapability(
            source_type=self.source_type,
            supported=False,
            reason="Instagram Graph API credentials are not configured. Use Manual URL Intake for posts.",
            documentation_note="Requires Meta App Review & instagram_basic / Business Discovery permissions.",
            requires_manual_fallback=True,
        )

    async def fetch_recent_posts(
        self,
        *,
        platform: str,
        profile_url: str,
        preferences: dict[str, Any],
        cursor: Optional[str] = None,
    ) -> list[NormalizedPost]:
        cap = self.check_access(platform)
        if not cap.supported:
            raise SourceAdapterError("SOURCE_UNAVAILABLE", cap.reason, transient=False)

        if platform == "instagram":
            # Instagram Graph API Business Discovery call (only when token & external username exist)
            username = preferences.get("ig_business_username")
            ig_user_id = preferences.get("ig_actor_id")
            if not username or not ig_user_id:
                raise SourceAdapterError(
                    "TARGET_MISSING_SCOPE",
                    "Instagram Business Discovery requires 'ig_actor_id' and 'ig_business_username' in target preferences.",
                    transient=False,
                )
            url = f"https://graph.facebook.com/v21.0/{ig_user_id}"
            params = {
                "fields": f"business_discovery.username({username}){{media.limit(5){{id,caption,permalink,media_type,timestamp}}}}",
                "access_token": self.settings.instagram_access_token,
            }
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, params=params)
            if resp.status_code == 429 or resp.status_code >= 500:
                raise SourceAdapterError("IG_TRANSIENT", f"Instagram API HTTP {resp.status_code}", transient=True)
            if resp.status_code >= 400:
                raise SourceAdapterError("IG_PERMISSION_ERROR", f"Instagram API HTTP {resp.status_code}", transient=False)
            media_items = (
                resp.json()
                .get("business_discovery", {})
                .get("media", {})
                .get("data", [])
            )
            return [
                self.normalize_post(
                    "instagram",
                    {
                        "post_url": item["permalink"],
                        "source_post_id": item["id"],
                        "author_name": username,
                        "author_url": profile_url,
                        "content_text": item.get("caption", ""),
                        "media_type": (item.get("media_type") or "image").lower(),
                        "source_metadata": {"official_api": True},
                    },
                )
                for item in media_items
                if item.get("permalink")
            ]

        raise SourceAdapterError(
            "LINKEDIN_SCOPE_RESTRICTED",
            "LinkedIn official API does not permit automated polling of arbitrary personal profiles; use manual post intake.",
            transient=False,
        )

    def normalize_post(self, platform: str, raw: dict[str, Any]) -> NormalizedPost:
        canon = validate_platform_url(platform, raw["post_url"])
        source_post_id = raw.get("source_post_id") or extract_post_id(platform, canon)
        content_text = (raw.get("content_text") or "").strip() or None
        return NormalizedPost(
            platform=platform,
            canonical_url=canon,
            source_post_id=source_post_id,
            dedupe_key=compute_dedupe_key(platform, source_post_id, canon),
            author_name=raw.get("author_name"),
            author_url=raw.get("author_url"),
            content_text=content_text,
            media_type=raw.get("media_type") or "text",
            published_at=raw.get("published_at"),
            content_hash=compute_content_hash(content_text),
            source_metadata={"intake_method": "official_api", **(raw.get("source_metadata") or {})},
        )

    async def health_check(self, platform: str) -> SourceHealth:
        cap = self.check_access(platform)
        return SourceHealth(
            healthy=cap.supported,
            status="configured" if cap.supported else "unsupported",
            details=cap.reason,
        )


def get_source_adapter(source_type: str, settings: Settings) -> SourceAdapter:
    adapters: dict[str, SourceAdapter] = {
        "manual": ManualAdapter(),
        "authorized_feed": AuthorizedFeedAdapter(settings),
        "notification_import": NotificationImportAdapter(),
        "official_api": OfficialAPIAdapter(settings),
    }
    adapter = adapters.get(source_type)
    if adapter is None:
        raise SourceAdapterError("UNKNOWN_SOURCE_TYPE", f"Unsupported source_type '{source_type}'.")
    return adapter
