"""Pydantic request and response schemas aligned with API_SPEC.md and DATABASE_SCHEMA.md."""

from datetime import datetime, time
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

PlatformType = Literal["linkedin", "instagram"]
SourceType = Literal["official_api", "authorized_feed", "notification_import", "manual"]
TargetStatus = Literal["active", "paused", "unsupported", "error"]
DraftStatus = Literal["pending", "edited", "copied", "opened", "skipped", "archived"]
DraftAction = Literal["copied", "opened", "skipped", "archived"]


class TargetCreateRequest(BaseModel):
    platform: PlatformType
    profile_url: str = Field(..., min_length=5, max_length=2048)
    display_name: Optional[str] = Field(default=None, max_length=160)
    source_type: SourceType = "manual"
    external_profile_id: Optional[str] = Field(default=None, max_length=255)
    preferences: dict[str, Any] = Field(default_factory=dict)


class TargetUpdateRequest(BaseModel):
    display_name: Optional[str] = Field(default=None, max_length=160)
    status: Optional[Literal["active", "paused"]] = None
    source_type: Optional[SourceType] = None
    preferences: Optional[dict[str, Any]] = None


class SourceCapabilityResponse(BaseModel):
    source_type: SourceType
    supported: bool
    reason: str
    documentation_note: str
    requires_manual_fallback: bool


class TargetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    platform: PlatformType
    profile_url: str
    display_name: Optional[str]
    source_type: SourceType
    external_profile_id: Optional[str]
    status: TargetStatus
    preferences: dict[str, Any]
    last_checked_at: Optional[datetime]
    last_success_at: Optional[datetime]
    last_error_code: Optional[str]
    created_at: datetime
    capability: Optional[SourceCapabilityResponse] = None


class ManualPostIngestRequest(BaseModel):
    platform: PlatformType
    post_url: str = Field(..., min_length=8, max_length=2048)
    target_id: Optional[UUID] = None
    author_name: Optional[str] = Field(default=None, max_length=160)
    content_text: Optional[str] = Field(default=None, max_length=10000)
    media_type: Optional[str] = Field(default="text", max_length=64)
    published_at: Optional[datetime] = None
    auto_generate_drafts: bool = True


class NotificationImportRequest(BaseModel):
    target_id: UUID
    posts: list[ManualPostIngestRequest] = Field(..., min_length=1, max_length=25)


class DraftSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    post_id: UUID
    draft_text: str
    edited_text: Optional[str]
    style_variant: Optional[str]
    relevance_score: Optional[float]
    quality_score: Optional[float]
    status: DraftStatus
    generation_model: Optional[str]
    generation_metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class PostResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    platform: PlatformType
    source_post_id: Optional[str]
    canonical_url: str
    author_name: Optional[str]
    author_url: Optional[str]
    content_text: Optional[str]
    media_type: Optional[str]
    status: str
    published_at: Optional[datetime]
    detected_at: datetime
    source_metadata: dict[str, Any]
    drafts: list[DraftSummaryResponse] = Field(default_factory=list)


class DraftWithPostResponse(DraftSummaryResponse):
    post: Optional[PostResponse] = None


class DraftGenerateRequest(BaseModel):
    variants: int = Field(default=2, ge=1, le=3)
    tone: Optional[str] = Field(default=None, max_length=64)
    length: Optional[Literal["short", "medium", "detailed"]] = None
    language: Optional[str] = Field(default=None, max_length=64)


class DraftUpdateRequest(BaseModel):
    edited_text: Optional[str] = Field(default=None, max_length=2000)
    status: Optional[DraftStatus] = None


class DraftRegenerateRequest(BaseModel):
    tone: Optional[str] = Field(default=None, max_length=64)
    length: Optional[Literal["short", "medium", "detailed"]] = None
    instruction: Optional[str] = Field(default=None, max_length=300)


class DraftMarkRequest(BaseModel):
    action: DraftAction


class PreferencesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    tone: str
    length: str
    language: str
    emoji_level: str
    relevance_threshold: float
    avoid_phrases: list[str]
    preferred_topics: list[str]
    excluded_topics: list[str]
    monitoring_interval_minutes: int
    data_retention_days: int
    updated_at: datetime


class PreferencesUpdateRequest(BaseModel):
    tone: Optional[str] = Field(default=None, max_length=64)
    length: Optional[Literal["short", "medium", "detailed"]] = None
    language: Optional[str] = Field(default=None, max_length=64)
    emoji_level: Optional[Literal["none", "low", "medium"]] = None
    relevance_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    avoid_phrases: Optional[list[str]] = Field(default=None, max_length=50)
    preferred_topics: Optional[list[str]] = Field(default=None, max_length=50)
    excluded_topics: Optional[list[str]] = Field(default=None, max_length=50)
    monitoring_interval_minutes: Optional[int] = Field(default=None, ge=5, le=1440)
    data_retention_days: Optional[int] = Field(default=None, ge=7, le=365)


class StyleSampleCreateRequest(BaseModel):
    sample_text: str = Field(..., min_length=5, max_length=1000)


class StyleSampleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    sample_text: str
    created_at: datetime


class NotificationSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    telegram_enabled: bool
    telegram_connected: bool
    telegram_chat_id_masked: Optional[str] = None
    daily_digest_enabled: bool
    digest_time: time
    updated_at: datetime


class NotificationSettingsUpdateRequest(BaseModel):
    telegram_enabled: Optional[bool] = None
    daily_digest_enabled: Optional[bool] = None
    digest_time: Optional[time] = None


class TelegramConnectResponse(BaseModel):
    verification_code: str
    expires_at: datetime
    bot_username: Optional[str]
    deep_link_url: Optional[str]
    instructions: str


class TelegramVerifyRequest(BaseModel):
    verification_code: str = Field(..., min_length=6, max_length=64)
    chat_id: str = Field(..., min_length=1, max_length=64)


class ActivityLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    event_type: str
    entity_type: Optional[str]
    entity_id: Optional[UUID]
    metadata: dict[str, Any] = Field(alias="metadata_json")
    created_at: datetime


class MonitoringJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    target_id: UUID
    status: str
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    items_found: int
    error_code: Optional[str]
    error_summary: Optional[str]
    created_at: datetime


class OverviewResponse(BaseModel):
    tracked_profiles: int
    active_profiles: int
    unsupported_profiles: int
    new_posts_detected: int
    drafts_awaiting_review: int
    drafts_approved_or_copied: int
    monitoring_health: Literal["healthy", "degraded", "idle"]
    last_checked_at: Optional[datetime]
    recent_activity: list[ActivityLogResponse]


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    display_name: Optional[str]
    timezone: str
    created_at: datetime


class ProfileUpdateRequest(BaseModel):
    display_name: Optional[str] = Field(default=None, max_length=120)
    timezone: Optional[str] = Field(default=None, max_length=64)


class InternalMonitorJobRequest(BaseModel):
    target_id: Optional[UUID] = None
    force: bool = False


class InternalProcessPostRequest(BaseModel):
    post_id: UUID
    user_id: UUID
    variants: int = Field(default=2, ge=1, le=3)
    notify_telegram: bool = True
