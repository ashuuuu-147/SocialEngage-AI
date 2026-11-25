"""Cloud monitoring job runner with exponential backoff, jitter, and idempotency."""

import asyncio
import random
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.engine import CommentEngine
from app.core.config import Settings
from app.models.entities import (
    ActivityLog,
    CommentDraft,
    MonitoringJob,
    NotificationSettings,
    Post,
    StyleSample,
    TargetPost,
    TrackedTarget,
    UserPost,
    UserPreferences,
)
from app.notifications.telegram import TelegramNotifier
from app.source_adapters import NormalizedPost, SourceAdapterError, get_source_adapter


async def run_with_backoff(coro_factory, max_attempts: int = 3, base_delay: float = 0.4):
    """Retry transient SourceAdapterErrors with bounded exponential backoff + jitter."""
    last_exc: Exception | None = None
    for attempt in range(max_attempts):
        try:
            return await coro_factory()
        except SourceAdapterError as exc:
            last_exc = exc
            if not exc.transient or attempt == max_attempts - 1:
                raise
            delay = base_delay * (2**attempt) + random.uniform(0, 0.25)
            await asyncio.sleep(delay)
    assert last_exc is not None
    raise last_exc


def check_user_ai_quota(db: Session, user_id: UUID, settings: Settings) -> tuple[bool, int]:
    """Check if user is within daily AI draft generation quota."""
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    used = db.scalar(
        select(func.count(CommentDraft.id)).where(
            CommentDraft.user_id == user_id,
            CommentDraft.created_at >= since,
        )
    ) or 0
    return used < settings.ai_daily_user_quota, int(used)


def persist_normalized_post(
    db: Session,
    *,
    normalized: NormalizedPost,
    target: Optional[TrackedTarget] = None,
    submitted_by_user_id: Optional[UUID] = None,
) -> tuple[Post, bool]:
    """Idempotently persist post via dedupe_key and associate target if provided."""
    existing = db.scalar(select(Post).where(Post.dedupe_key == normalized.dedupe_key))
    created = False
    if existing is None:
        existing = Post(
            platform=normalized.platform,
            source_post_id=normalized.source_post_id,
            canonical_url=normalized.canonical_url,
            dedupe_key=normalized.dedupe_key,
            submitted_by_user_id=submitted_by_user_id or (target.user_id if target else None),
            author_name=normalized.author_name or (target.display_name if target else None),
            author_url=normalized.author_url or (target.profile_url if target else None),
            content_text=normalized.content_text,
            media_type=normalized.media_type,
            published_at=normalized.published_at,
            content_hash=normalized.content_hash,
            source_metadata=normalized.source_metadata,
            status="discovered",
        )
        db.add(existing)
        db.flush()
        created = True

    if target is not None:
        link = db.scalar(
            select(TargetPost).where(
                TargetPost.target_id == target.id,
                TargetPost.post_id == existing.id,
            )
        )
        if link is None:
            db.add(TargetPost(target_id=target.id, post_id=existing.id))

    owner_uid = submitted_by_user_id or (target.user_id if target else None)
    if owner_uid is not None:
        user_link = db.scalar(
            select(UserPost).where(
                UserPost.user_id == owner_uid,
                UserPost.post_id == existing.id,
            )
        )
        if user_link is None:
            db.add(UserPost(user_id=owner_uid, post_id=existing.id))

    db.commit()
    db.refresh(existing)
    return existing, created


async def process_post_for_user(
    db: Session,
    *,
    post: Post,
    user_id: UUID,
    settings: Settings,
    variants: int = 2,
    notify_telegram: bool = True,
    force_regenerate: bool = False,
) -> list[CommentDraft]:
    """Run relevance filtering, AI drafting, scoring, and optional Telegram notification."""
    if not force_regenerate:
        existing_drafts = list(
            db.scalars(
                select(CommentDraft).where(
                    CommentDraft.post_id == post.id,
                    CommentDraft.user_id == user_id,
                )
            )
        )
        if existing_drafts:
            return existing_drafts

    within_quota, used_count = check_user_ai_quota(db, user_id, settings)
    if not within_quota:
        db.add(
            ActivityLog(
                user_id=user_id,
                event_type="ai_quota_exhausted",
                entity_type="post",
                entity_id=post.id,
                metadata_json={"used_24h": used_count, "limit": settings.ai_daily_user_quota},
            )
        )
        db.commit()
        return []

    prefs = db.get(UserPreferences, user_id)
    samples = list(
        db.scalars(
            select(StyleSample.sample_text)
            .where(StyleSample.user_id == user_id)
            .order_by(StyleSample.created_at.desc())
            .limit(4)
        )
    )
    recent_drafts = list(
        db.scalars(
            select(CommentDraft.draft_text)
            .where(CommentDraft.user_id == user_id)
            .order_by(CommentDraft.created_at.desc())
            .limit(8)
        )
    )

    post.status = "analyzing"
    db.commit()

    engine = CommentEngine(settings)
    result = await engine.generate_drafts(
        platform=post.platform,
        author_name=post.author_name or "Creator",
        content_text=post.content_text or "",
        media_type=post.media_type or "text",
        tone=prefs.tone if prefs else "professional-conversational",
        length=prefs.length if prefs else "short",
        language=prefs.language if prefs else "English",
        emoji_level=prefs.emoji_level if prefs else "low",
        relevance_threshold=float(prefs.relevance_threshold) if prefs else 0.70,
        variants=variants,
        preferred_topics=prefs.preferred_topics if prefs else [],
        excluded_topics=prefs.excluded_topics if prefs else [],
        avoid_phrases=prefs.avoid_phrases if prefs else [],
        style_samples=samples,
        recent_comments=recent_drafts,
    )

    if result.should_skip or not result.drafts:
        post.status = "skipped"
        post.source_metadata = {
            **(post.source_metadata or {}),
            "skip_reason": result.skip_reason,
            "topic": result.topic,
            "relevance_score": result.relevance_score,
        }
        db.add(
            ActivityLog(
                user_id=user_id,
                event_type="post_skipped",
                entity_type="post",
                entity_id=post.id,
                metadata_json={
                    "reason": result.skip_reason,
                    "relevance_score": result.relevance_score,
                    "topic": result.topic,
                },
            )
        )
        db.commit()
        return []

    saved_drafts: list[CommentDraft] = []
    for item in result.drafts:
        draft = CommentDraft(
            user_id=user_id,
            post_id=post.id,
            draft_text=item.text,
            style_variant=item.style,
            relevance_score=item.relevance_score,
            quality_score=item.quality_score,
            status="pending",
            generation_model=result.model_used,
            generation_metadata={
                "topic": result.topic,
                "quality_breakdown": item.quality_breakdown,
                "repetition_similarity": item.repetition_similarity,
                "below_threshold": item.below_threshold,
                "warnings": item.warnings,
            },
        )
        db.add(draft)
        saved_drafts.append(draft)

    post.status = "drafted"
    db.flush()

    db.add(
        ActivityLog(
            user_id=user_id,
            event_type="drafts_generated",
            entity_type="post",
            entity_id=post.id,
            metadata_json={"count": len(saved_drafts), "topic": result.topic},
        )
    )
    db.commit()
    for d in saved_drafts:
        db.refresh(d)

    if notify_telegram and saved_drafts:
        notif = db.get(NotificationSettings, user_id)
        if notif and notif.telegram_enabled and notif.telegram_chat_id:
            notifier = TelegramNotifier(settings)
            msg = notifier.format_draft_notification(
                platform=post.platform,
                author_name=post.author_name or "Watched Profile",
                post_preview=post.content_text or post.canonical_url,
                draft_text=saved_drafts[0].draft_text,
                post_url=post.canonical_url,
                draft_id=str(saved_drafts[0].id),
            )
            delivery = await notifier.send_message(notif.telegram_chat_id, msg)
            db.add(
                ActivityLog(
                    user_id=user_id,
                    event_type="telegram_notification_sent" if delivery.delivered else "telegram_notification_failed",
                    entity_type="draft",
                    entity_id=saved_drafts[0].id,
                    metadata_json={"mode": delivery.mode, "detail": delivery.detail},
                )
            )
            db.commit()

    return saved_drafts


async def run_monitoring_cycle(
    db: Session,
    settings: Settings,
    *,
    target_id: Optional[UUID] = None,
    force: bool = False,
) -> dict:
    """Execute scheduled monitoring check across active targets."""
    query = select(TrackedTarget).where(TrackedTarget.status == "active")
    if target_id:
        query = query.where(TrackedTarget.id == target_id)
    targets = list(db.scalars(query))

    summary = {"checked": 0, "new_posts": 0, "drafts_created": 0, "errors": 0, "unsupported": 0}
    now = datetime.now(timezone.utc)

    for target in targets:
        if target.source_type == "manual":
            continue

        job = MonitoringJob(target_id=target.id, status="running", started_at=now)
        db.add(job)
        db.flush()

        try:
            adapter = get_source_adapter(target.source_type, settings)
            cap = adapter.check_access(target.platform)
            if not cap.supported:
                target.status = "unsupported"
                target.last_checked_at = now
                target.last_error_code = "SOURCE_UNAVAILABLE"
                job.status = "failed"
                job.finished_at = datetime.now(timezone.utc)
                job.error_code = "SOURCE_UNAVAILABLE"
                job.error_summary = cap.reason
                db.add(
                    ActivityLog(
                        user_id=target.user_id,
                        event_type="source_unsupported",
                        entity_type="target",
                        entity_id=target.id,
                        metadata_json={"reason": cap.reason, "source_type": target.source_type},
                    )
                )
                db.commit()
                summary["unsupported"] += 1
                continue

            posts = await run_with_backoff(
                lambda a=adapter, t=target: a.fetch_recent_posts(
                    platform=t.platform,
                    profile_url=t.profile_url,
                    preferences={**(t.preferences or {}), "display_name": t.display_name},
                )
            )

            new_count = 0
            for norm in posts:
                post, created = persist_normalized_post(db, normalized=norm, target=target)
                if created:
                    new_count += 1
                    drafts = await process_post_for_user(
                        db, post=post, user_id=target.user_id, settings=settings
                    )
                    summary["drafts_created"] += len(drafts)

            target.last_checked_at = now
            target.last_success_at = datetime.now(timezone.utc)
            target.last_error_code = None
            job.status = "success"
            job.finished_at = datetime.now(timezone.utc)
            job.items_found = new_count
            db.add(
                ActivityLog(
                    user_id=target.user_id,
                    event_type="target_checked",
                    entity_type="target",
                    entity_id=target.id,
                    metadata_json={"items_found": new_count, "source_type": target.source_type},
                )
            )
            db.commit()
            summary["checked"] += 1
            summary["new_posts"] += new_count

        except SourceAdapterError as exc:
            target.last_checked_at = now
            target.last_error_code = exc.code
            if not exc.transient:
                target.status = "error"
            job.status = "failed"
            job.finished_at = datetime.now(timezone.utc)
            job.error_code = exc.code
            job.error_summary = exc.message
            db.add(
                ActivityLog(
                    user_id=target.user_id,
                    event_type="target_check_failed",
                    entity_type="target",
                    entity_id=target.id,
                    metadata_json={"error_code": exc.code, "message": exc.message},
                )
            )
            db.commit()
            summary["errors"] += 1

    return summary


async def run_daily_digest_cycle(db: Session, settings: Settings) -> dict:
    """Send daily digest to users who enabled it and have verified Telegram chats."""
    notif_rows = list(
        db.scalars(
            select(NotificationSettings).where(
                NotificationSettings.daily_digest_enabled.is_(True),
                NotificationSettings.telegram_enabled.is_(True),
                NotificationSettings.telegram_chat_id.is_not(None),
            )
        )
    )
    notifier = TelegramNotifier(settings)
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    sent = 0

    for row in notif_rows:
        posts_count = db.scalar(
            select(func.count(Post.id)).where(
                Post.submitted_by_user_id == row.user_id,
                Post.detected_at >= since,
            )
        ) or 0
        drafts_pending = db.scalar(
            select(func.count(CommentDraft.id)).where(
                CommentDraft.user_id == row.user_id,
                CommentDraft.status == "pending",
            )
        ) or 0
        skipped_count = db.scalar(
            select(func.count(Post.id)).where(
                Post.submitted_by_user_id == row.user_id,
                Post.status == "skipped",
                Post.detected_at >= since,
            )
        ) or 0
        msg = notifier.format_daily_digest(
            posts_count=int(posts_count),
            drafts_pending=int(drafts_pending),
            skipped_count=int(skipped_count),
        )
        result = await notifier.send_message(row.telegram_chat_id or "", msg)
        if result.delivered:
            sent += 1
            db.add(
                ActivityLog(
                    user_id=row.user_id,
                    event_type="daily_digest_sent",
                    entity_type="notification",
                    metadata_json={"mode": result.mode},
                )
            )
            db.commit()

    return {"digests_sent": sent}
