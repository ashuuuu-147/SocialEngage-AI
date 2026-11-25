"""Base SourceAdapter interface, URL canonicalization, SSRF guard, and normalized DTOs."""

import hashlib
import ipaddress
import re
import socket
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


class SourceAdapterError(Exception):
    def __init__(self, code: str, message: str, transient: bool = False) -> None:
        self.code = code
        self.message = message
        self.transient = transient
        super().__init__(message)


@dataclass
class SourceCapability:
    source_type: str
    supported: bool
    reason: str
    documentation_note: str
    requires_manual_fallback: bool


@dataclass
class NormalizedPost:
    platform: str
    canonical_url: str
    source_post_id: Optional[str]
    dedupe_key: str
    author_name: Optional[str]
    author_url: Optional[str]
    content_text: Optional[str]
    media_type: str = "text"
    published_at: Optional[datetime] = None
    content_hash: Optional[str] = None
    source_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SourceHealth:
    healthy: bool
    status: str
    details: str
    rate_limit_remaining: Optional[int] = None


TRACKING_QUERY_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "igsh",
    "igshid",
    "rcm",
    "trk",
    "lipi",
}


def canonicalize_url(raw_url: str) -> str:
    """Normalize URL scheme, host, path, and strip tracking query parameters."""
    parsed = urlparse(raw_url.strip())
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise SourceAdapterError("INVALID_URL", "URL must use http or https and include a valid host.")
    scheme = "https"
    netloc = parsed.netloc.lower()
    if netloc.startswith("m."):
        netloc = "www." + netloc[2:]
    path = re.sub(r"/+$", "", parsed.path) or "/"
    filtered_qs = [
        (k, v)
        for k, v in parse_qsl(parsed.query, keep_blank_values=False)
        if k.lower() not in TRACKING_QUERY_PARAMS
    ]
    query = urlencode(sorted(filtered_qs))
    return urlunparse((scheme, netloc, path, "", query, ""))


def validate_public_http_url(raw_url: str) -> str:
    """Validate URL and block loopback/private/link-local targets (SSRF prevention)."""
    canon = canonicalize_url(raw_url)
    parsed = urlparse(canon)
    host = parsed.hostname or ""
    if host in ("localhost", "localhost.localdomain") or host.endswith(".local"):
        raise SourceAdapterError("UNSAFE_URL", "Local or internal network URLs are not permitted.")
    try:
        ip_obj = ipaddress.ip_address(host)
        if (
            ip_obj.is_private
            or ip_obj.is_loopback
            or ip_obj.is_link_local
            or ip_obj.is_multicast
            or ip_obj.is_reserved
        ):
            raise SourceAdapterError("UNSAFE_URL", "Private or loopback IP addresses are not permitted.")
    except ValueError:
        # Hostname — resolve DNS safely if possible
        try:
            infos = socket.getaddrinfo(host, None)
            for info in infos:
                addr = info[4][0]
                ip_resolved = ipaddress.ip_address(addr)
                if (
                    ip_resolved.is_private
                    or ip_resolved.is_loopback
                    or ip_resolved.is_link_local
                    or ip_resolved.is_reserved
                ):
                    raise SourceAdapterError(
                        "UNSAFE_URL", "Target hostname resolves to a non-public IP address."
                    )
        except socket.gaierror:
            # Allow offline validation for domain syntax in isolated test environments
            pass
    return canon


def extract_post_id(platform: str, canonical_url: str) -> Optional[str]:
    parsed = urlparse(canonical_url)
    path = parsed.path
    if platform == "linkedin":
        m = re.search(r"(urn:li:(?:activity|ugcPost|share):\d+)", canonical_url)
        if m:
            return m.group(1)
        m2 = re.search(r"/posts/[^/]+-(\d+)", path)
        if m2:
            return m2.group(1)
    elif platform == "instagram":
        m = re.search(r"/(?:p|reel|tv)/([A-Za-z0-9_-]+)", path)
        if m:
            return m.group(1)
    return None


def compute_dedupe_key(platform: str, source_post_id: Optional[str], canonical_url: str) -> str:
    if source_post_id:
        return f"{platform}:id:{source_post_id}"
    return f"{platform}:url:{canonical_url}"


def compute_content_hash(content_text: Optional[str]) -> Optional[str]:
    if not content_text:
        return None
    normalized = " ".join(content_text.split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class SourceAdapter(ABC):
    source_type: str

    @abstractmethod
    def validate_target(self, platform: str, profile_url: str) -> str:
        """Validate target URL and return canonical URL."""

    @abstractmethod
    def check_access(self, platform: str) -> SourceCapability:
        """Return honest capability and authorization status for the platform."""

    @abstractmethod
    async def fetch_recent_posts(
        self,
        *,
        platform: str,
        profile_url: str,
        preferences: dict[str, Any],
        cursor: Optional[str] = None,
    ) -> list[NormalizedPost]:
        """Fetch permitted recent posts for a target."""

    @abstractmethod
    def normalize_post(self, platform: str, raw: dict[str, Any]) -> NormalizedPost:
        """Convert raw source payload into NormalizedPost."""

    @abstractmethod
    async def health_check(self, platform: str) -> SourceHealth:
        """Return adapter operational status."""
