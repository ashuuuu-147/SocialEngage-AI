"""Post intake, listing, and draft generation endpoints."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.core.security import AuthenticatedUser, get_current_user, rate_limiter
from app.db.session import get_db
from app.models.entities import Post, TargetPost, TrackedTarget, UserPost, UserPreferences
from app.schemas.api import (
    DraftGenerateRequest,
    DraftSummaryResponse,
    ManualPostIngestRequest,
    NotificationImportRequest,
    PostResponse,
)
from app.services.ownership import get_owned_post, get_owned_target, log_activity
from app.source_adapters import ManualAdapter, NotificationImportAdapter, SourceAdapterError
from app.workers.monitoring import persist_normalized_post, process_post_for_user

router = APIRouter(tags=["posts"])


def _serialize_post(post: Post, user_id: UUID) -> PostResponse:
    user_drafts = [d for d in post.drafts if d.user_id == user_id]
    return PostResponse(
        id=post.id,
        platform=post.platform,
        source_post_id=post.source_post_id,
        canonical_url=post.canonical_url,
        author_name=post.author_name,
        author_url=post.author_url,
        content_text=post.content_text,
        media_type=post.media_type,
        status=post.status,
        published_at=post.published_at,
        detected_at=post.detected_at,
        source_metadata=post.source_metadata or {},
        drafts=[DraftSummaryResponse.model_validate(d) for d in user_drafts],
    )


@router.post("/posts/ingest-manual", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def ingest_manual_post(
    payload: ManualPostIngestRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    rate_limiter.check(f"ingest:{user.user_id}", max_requests=30, window_seconds=60)

    target: Optional[TrackedTarget] = None
    if payload.target_id is not None:
        target = get_owned_target(db, user.user_id, payload.target_id)
        if target.platform != payload.platform:
            raise AppError(
                "PLATFORM_MISMATCH",
                "Post platform does not match the selected target's platform.",
                400,
            )

    adapter = ManualAdapter()
    try:
        normalized = adapter.normalize_post(
            payload.platform,
            {
                "post_url": payload.post_url,
                "author_name": payload.author_name or (target.display_name if target else None),
                "author_url": target.profile_url if target else None,
                "content_text": payload.content_text,
                "media_type": payload.media_type,
                "published_at": payload.published_at,
            },
        )
    except SourceAdapterError as exc:
        raise AppError(exc.code, exc.message, 400) from exc

    post, created = persist_normalized_post(
        db,
        normalized=normalized,
        target=target,
        submitted_by_user_id=user.user_id,
    )

    if created:
        log_activity(
            db,
            user_id=user.user_id,
            event_type="post_ingested_manual",
            entity_type="post",
            entity_id=post.id,
            metadata={"platform": post.platform, "canonical_url": post.canonical_url},
        )
        db.commit()

    if payload.auto_generate_drafts and post.content_text:
        await process_post_for_user(
            db,
            post=post,
            user_id=user.user_id,
            settings=settings,
            variants=2,
            notify_telegram=True,
        )

    reloaded = db.scalar(
        select(Post).options(selectinload(Post.drafts)).where(Post.id == post.id)
    )
    assert reloaded is not None
    return _serialize_post(reloaded, user.user_id)


@router.post("/posts/import-notifications", status_code=status.HTTP_201_CREATED)
async def import_notification_posts(
    payload: NotificationImportRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    target = get_owned_target(db, user.user_id, payload.target_id)
    adapter = NotificationImportAdapter()
    imported = 0
    duplicates = 0

    for item in payload.posts:
        try:
            normalized = adapter.normalize_post(
                target.platform,
                {
                    "post_url": item.post_url,
                    "author_name": item.author_name or target.display_name,
                    "author_url": target.profile_url,
                    "content_text": item.content_text,
                    "media_type": item.media_type,
                    "published_at": item.published_at,
                },
            )
        except SourceAdapterError as exc:
            raise AppError(exc.code, exc.message, 400) from exc

        post, created = persist_normalized_post(
            db, normalized=normalized, target=target, submitted_by_user_id=user.user_id
        )
        if created:
            imported += 1
            if item.auto_generate_drafts and post.content_text:
                await process_post_for_user(db, post=post, user_id=user.user_id, settings=settings)
        else:
            duplicates += 1

    return {"imported": imported, "duplicates": duplicates}


@router.get("/posts", response_model=list[PostResponse])
def list_posts(
    platform: Optional[str] = Query(default=None),
    target_id: Optional[UUID] = Query(default=None),
    post_status: Optional[str] = Query(default=None, alias="status"),
    since: Optional[datetime] = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=25, ge=1, le=100),
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    owned_target_ids = select(TrackedTarget.id).where(TrackedTarget.user_id == user.user_id)
    linked_post_ids = select(TargetPost.post_id).where(TargetPost.target_id.in_(owned_target_ids))
    user_post_ids = select(UserPost.post_id).where(UserPost.user_id == user.user_id)

    stmt = (
        select(Post)
        .options(selectinload(Post.drafts))
        .where(
            or_(
                Post.submitted_by_user_id == user.user_id,
                Post.id.in_(user_post_ids),
                Post.id.in_(linked_post_ids),
            )
        )
    )
    if platform:
        stmt = stmt.where(Post.platform == platform)
    if post_status:
        stmt = stmt.where(Post.status == post_status)
    if since:
        stmt = stmt.where(Post.detected_at >= since)
    if target_id:
        get_owned_target(db, user.user_id, target_id)
        target_post_ids = select(TargetPost.post_id).where(TargetPost.target_id == target_id)
        stmt = stmt.where(Post.id.in_(target_post_ids))

    stmt = stmt.order_by(Post.detected_at.desc()).offset((page - 1) * limit).limit(limit)
    posts = list(db.scalars(stmt))
    return [_serialize_post(p, user.user_id) for p in posts]


@router.get("/posts/{post_id}", response_model=PostResponse)
def get_post(
    post_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = get_owned_post(db, user.user_id, post_id)
    reloaded = db.scalar(select(Post).options(selectinload(Post.drafts)).where(Post.id == post.id))
    assert reloaded is not None
    return _serialize_post(reloaded, user.user_id)


@router.post("/posts/{post_id}/drafts", response_model=list[DraftSummaryResponse], status_code=status.HTTP_201_CREATED)
async def generate_drafts_for_post(
    post_id: UUID,
    payload: DraftGenerateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    rate_limiter.check(f"ai_gen:{user.user_id}", max_requests=20, window_seconds=60)
    post = get_owned_post(db, user.user_id, post_id)

    if not post.content_text:
        raise AppError(
            "POST_TEXT_REQUIRED",
            "Post has no text preview to generate a context-specific comment.",
            400,
        )

    # Temporarily apply per-request tone/length/language if provided
    prefs = db.get(UserPreferences, user.user_id)
    orig_vals = None
    if prefs and (payload.tone or payload.length or payload.language):
        orig_vals = (prefs.tone, prefs.length, prefs.language)
        if payload.tone:
            prefs.tone = payload.tone
        if payload.length:
            prefs.length = payload.length
        if payload.language:
            prefs.language = payload.language
        db.flush()

    try:
        drafts = await process_post_for_user(
            db,
            post=post,
            user_id=user.user_id,
            settings=settings,
            variants=payload.variants,
            notify_telegram=False,
            force_regenerate=True,
        )
    finally:
        if prefs and orig_vals:
            prefs.tone, prefs.length, prefs.language = orig_vals
            db.commit()

    return [DraftSummaryResponse.model_validate(d) for d in drafts]
