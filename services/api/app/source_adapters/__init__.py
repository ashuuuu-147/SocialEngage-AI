"""Source adapters exports."""

from app.source_adapters.adapters import (
    AuthorizedFeedAdapter,
    ManualAdapter,
    NotificationImportAdapter,
    OfficialAPIAdapter,
    get_source_adapter,
    validate_platform_url,
)
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

__all__ = [
    "AuthorizedFeedAdapter",
    "ManualAdapter",
    "NormalizedPost",
    "NotificationImportAdapter",
    "OfficialAPIAdapter",
    "SourceAdapter",
    "SourceAdapterError",
    "SourceCapability",
    "SourceHealth",
    "canonicalize_url",
    "compute_content_hash",
    "compute_dedupe_key",
    "extract_post_id",
    "get_source_adapter",
    "validate_platform_url",
    "validate_public_http_url",
]
