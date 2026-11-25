"""SQLAlchemy 2.0 models matching DATABASE_SCHEMA.md."""

import uuid
from datetime import datetime, time, timezone
from typing import Any, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from app.db.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class StringListType(TypeDecorator):
    """Stores list[str] as PostgreSQL text[] and SQLite JSON."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(ARRAY(Text))
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, dialect):
        if value is None:
            return []
        return list(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return []
        return list(value)


JSONType = JSON().with_variant(JSONB(), "postgresql")


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    display_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timezone: Mapped[str] = mapped_column(Text, default="Asia/Kolkata", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    targets: Mapped[list["TrackedTarget"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    drafts: Mapped[list["CommentDraft"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    preferences: Mapped[Optional["UserPreferences"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    style_samples: Mapped[list["StyleSample"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    notification_settings: Mapped[Optional["NotificationSettings"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    activity_logs: Mapped[list["ActivityLog"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class TrackedTarget(Base):
    __tablename__ = "tracked_targets"
    __table_args__ = (
        CheckConstraint("platform in ('linkedin','instagram')", name="ck_targets_platform"),
        CheckConstraint(
            "source_type in ('official_api','authorized_feed','notification_import','manual')",
            name="ck_targets_source_type",
        ),
        CheckConstraint(
            "status in ('active','paused','unsupported','error')",
            name="ck_targets_status",
        ),
        UniqueConstraint("user_id", "platform", "profile_url", name="uq_targets_user_platform_url"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    profile_url: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    external_profile_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    preferences: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict, nullable=False)
    last_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_success_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    user: Mapped["Profile"] = relationship(back_populates="targets")
    target_posts: Mapped[list["TargetPost"]] = relationship(
        back_populates="target", cascade="all, delete-orphan"
    )
    monitoring_jobs: Mapped[list["MonitoringJob"]] = relationship(
        back_populates="target", cascade="all, delete-orphan"
    )


class Post(Base):
    __tablename__ = "posts"
    __table_args__ = (
        CheckConstraint("platform in ('linkedin','instagram')", name="ck_posts_platform"),
        CheckConstraint(
            "status in ('discovered','analyzing','drafted','skipped','error')",
            name="ck_posts_status",
        ),
        UniqueConstraint("dedupe_key", name="uq_posts_dedupe_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    source_post_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    canonical_url: Mapped[str] = mapped_column(Text, nullable=False)
    dedupe_key: Mapped[str] = mapped_column(Text, nullable=False)
    submitted_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True
    )
    author_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    author_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    media_type: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="discovered", nullable=False)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    content_hash: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_metadata: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict, nullable=False)

    target_posts: Mapped[list["TargetPost"]] = relationship(
        back_populates="post", cascade="all, delete-orphan"
    )
    user_posts: Mapped[list["UserPost"]] = relationship(
        back_populates="post", cascade="all, delete-orphan"
    )
    drafts: Mapped[list["CommentDraft"]] = relationship(
        back_populates="post", cascade="all, delete-orphan"
    )


class UserPost(Base):
    __tablename__ = "user_posts"
    __table_args__ = (UniqueConstraint("user_id", "post_id", name="uq_user_posts_user_post"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    post_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("posts.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    post: Mapped["Post"] = relationship(back_populates="user_posts")


class TargetPost(Base):
    __tablename__ = "target_posts"
    __table_args__ = (UniqueConstraint("target_id", "post_id", name="uq_target_posts_target_post"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    target_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tracked_targets.id", ondelete="CASCADE"), nullable=False
    )
    post_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("posts.id", ondelete="CASCADE"), nullable=False
    )
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    target: Mapped["TrackedTarget"] = relationship(back_populates="target_posts")
    post: Mapped["Post"] = relationship(back_populates="target_posts")


class CommentDraft(Base):
    __tablename__ = "comment_drafts"
    __table_args__ = (
        CheckConstraint(
            "status in ('pending','edited','copied','opened','skipped','archived')",
            name="ck_drafts_status",
        ),
        Index("idx_drafts_user_status_created", "user_id", "status", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    post_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("posts.id", ondelete="CASCADE"), nullable=False
    )
    draft_text: Mapped[str] = mapped_column(Text, nullable=False)
    edited_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    style_variant: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    relevance_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    quality_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    generation_model: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    generation_metadata: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    user: Mapped["Profile"] = relationship(back_populates="drafts")
    post: Mapped["Post"] = relationship(back_populates="drafts")


class UserPreferences(Base):
    __tablename__ = "user_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True
    )
    tone: Mapped[str] = mapped_column(Text, default="professional-conversational", nullable=False)
    length: Mapped[str] = mapped_column(Text, default="short", nullable=False)
    language: Mapped[str] = mapped_column(Text, default="English", nullable=False)
    emoji_level: Mapped[str] = mapped_column(Text, default="low", nullable=False)
    relevance_threshold: Mapped[float] = mapped_column(Numeric(5, 2), default=0.70, nullable=False)
    avoid_phrases: Mapped[list[str]] = mapped_column(StringListType, default=list, nullable=False)
    preferred_topics: Mapped[list[str]] = mapped_column(StringListType, default=list, nullable=False)
    excluded_topics: Mapped[list[str]] = mapped_column(StringListType, default=list, nullable=False)
    monitoring_interval_minutes: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    data_retention_days: Mapped[int] = mapped_column(Integer, default=90, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    user: Mapped["Profile"] = relationship(back_populates="preferences")


class StyleSample(Base):
    __tablename__ = "style_samples"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    sample_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    user: Mapped["Profile"] = relationship(back_populates="style_samples")


class NotificationSettings(Base):
    __tablename__ = "notification_settings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True
    )
    telegram_chat_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    telegram_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    telegram_verification_code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    telegram_verification_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    daily_digest_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    digest_time: Mapped[time] = mapped_column(Time, default=time(19, 0), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    user: Mapped["Profile"] = relationship(back_populates="notification_settings")


class MonitoringJob(Base):
    __tablename__ = "monitoring_jobs"
    __table_args__ = (
        CheckConstraint(
            "status in ('queued','running','success','partial','failed')",
            name="ck_monitoring_jobs_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    target_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tracked_targets.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    items_found: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    target: Mapped["TrackedTarget"] = relationship(back_populates="monitoring_jobs")


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    entity_type: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid(as_uuid=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONType, default=dict, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    user: Mapped["Profile"] = relationship(back_populates="activity_logs")
