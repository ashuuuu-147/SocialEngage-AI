"""Comment draft review, edit, regenerate, and human-action endpoints (never auto-publish)."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.ai.engine import CommentEngine
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.core.security import AuthenticatedUser, get_current_user, rate_limiter
from app.db.session import get_db
from app.models.entities import CommentDraft, Post, StyleSample, UserPreferences
from app.schemas.api import (
    DraftMarkRequest,
    DraftRegenerateRequest,
    DraftSummaryResponse,
    DraftUpdateRequest,
    DraftWithPostResponse,
    PostResponse,
)
from app.services.ownership import get_owned_draft, log_activity
from app.workers.monitoring import check_user_ai_quota

router = APIRouter(tags=["drafts"])


def _to_draft_with_post(draft: CommentDraft) -> DraftWithPostResponse:
    post_obj = None
    if draft.post:
        post_obj = PostResponse(
            id=draft.post.id,
            platform=draft.post.platform,
            source_post_id=draft.post.source_post_id,
            canonical_url=draft.post.canonical_url,
            author_name=draft.post.author_name,
            author_url=draft.post.author_url,
            content_text=draft.post.content_text,
            media_type=draft.post.media_type,
            status=draft.post.status,
            published_at=draft.post.published_at,
            detected_at=draft.post.detected_at,
            source_metadata=draft.post.source_metadata or {},
            drafts=[],
        )
    return DraftWithPostResponse(
        id=draft.id,
        user_id=draft.user_id,
        post_id=draft.post_id,
        draft_text=draft.draft_text,
        edited_text=draft.edited_text,
        style_variant=draft.style_variant,
        relevance_score=float(draft.relevance_score) if draft.relevance_score is not None else None,
        quality_score=float(draft.quality_score) if draft.quality_score is not None else None,
        status=draft.status,
        generation_model=draft.generation_model,
        generation_metadata=draft.generation_metadata or {},
        created_at=draft.created_at,
        updated_at=draft.updated_at,
        post=post_obj,
    )


@router.get("/drafts", response_model=list[DraftWithPostResponse])
def list_drafts(
    draft_status: Optional[str] = Query(default=None, alias="status"),
    platform: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=25, ge=1, le=100),
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = (
        select(CommentDraft)
        .options(selectinload(CommentDraft.post))
        .where(CommentDraft.user_id == user.user_id)
    )
    if draft_status:
        stmt = stmt.where(CommentDraft.status == draft_status)
    if platform:
        stmt = stmt.join(Post, Post.id == CommentDraft.post_id).where(Post.platform == platform)
    stmt = stmt.order_by(CommentDraft.created_at.desc()).offset((page - 1) * limit).limit(limit)
    rows = list(db.scalars(stmt))
    return [_to_draft_with_post(d) for d in rows]


@router.patch("/drafts/{draft_id}", response_model=DraftSummaryResponse)
def update_draft(
    draft_id: UUID,
    payload: DraftUpdateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    draft = get_owned_draft(db, user.user_id, draft_id)
    if payload.edited_text is not None:
        draft.edited_text = payload.edited_text.strip()
        if payload.status is None:
            draft.status = "edited"
    if payload.status is not None:
        draft.status = payload.status

    log_activity(
        db,
        user_id=user.user_id,
        event_type="draft_edited",
        entity_type="draft",
        entity_id=draft.id,
        metadata={"status": draft.status},
    )
    db.commit()
    db.refresh(draft)
    return DraftSummaryResponse.model_validate(draft)


@router.post("/drafts/{draft_id}/regenerate", response_model=DraftSummaryResponse)
async def regenerate_draft(
    draft_id: UUID,
    payload: DraftRegenerateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    rate_limiter.check(f"ai_regen:{user.user_id}", max_requests=20, window_seconds=60)
    draft = get_owned_draft(db, user.user_id, draft_id)

    within_quota, used = check_user_ai_quota(db, user.user_id, settings)
    if not within_quota:
        raise AppError(
            "AI_QUOTA_EXCEEDED",
            f"Daily AI draft quota reached ({used}/{settings.ai_daily_user_quota}).",
            429,
        )

    post = db.get(Post, draft.post_id)
    if post is None or not post.content_text:
        raise AppError("POST_TEXT_REQUIRED", "Original post content is missing.", 400)

    prefs = db.get(UserPreferences, user.user_id)
    samples = list(
        db.scalars(
            select(StyleSample.sample_text)
            .where(StyleSample.user_id == user.user_id)
            .limit(4)
        )
    )
    recent_texts = list(
        db.scalars(
            select(CommentDraft.draft_text)
            .where(CommentDraft.user_id == user.user_id)
            .order_by(CommentDraft.created_at.desc())
            .limit(8)
        )
    )

    engine = CommentEngine(settings)
    result = await engine.generate_drafts(
        platform=post.platform,
        author_name=post.author_name or "Creator",
        content_text=post.content_text,
        media_type=post.media_type or "text",
        tone=payload.tone or (prefs.tone if prefs else "professional-conversational"),
        length=payload.length or (prefs.length if prefs else "short"),
        language=prefs.language if prefs else "English",
        emoji_level=prefs.emoji_level if prefs else "low",
        relevance_threshold=0.0,  # Explicit user regeneration always returns a draft
        variants=1,
        preferred_topics=prefs.preferred_topics if prefs else [],
        excluded_topics=[],
        avoid_phrases=prefs.avoid_phrases if prefs else [],
        style_samples=samples,
        recent_comments=recent_texts,
        custom_instruction=payload.instruction,
    )

    if not result.drafts:
        raise AppError(
            "REGENERATION_SKIPPED",
            result.skip_reason or "Could not regenerate a safe draft for this post.",
            400,
        )

    new_opt = result.drafts[0]
    draft.draft_text = new_opt.text
    draft.edited_text = None
    draft.style_variant = new_opt.style
    draft.relevance_score = new_opt.relevance_score
    draft.quality_score = new_opt.quality_score
    draft.status = "pending"
    draft.generation_model = result.model_used
    draft.generation_metadata = {
        "topic": result.topic,
        "quality_breakdown": new_opt.quality_breakdown,
        "repetition_similarity": new_opt.repetition_similarity,
        "regenerated": True,
        "instruction": payload.instruction,
    }

    log_activity(
        db,
        user_id=user.user_id,
        event_type="draft_regenerated",
        entity_type="draft",
        entity_id=draft.id,
        metadata={"tone": payload.tone, "quality_score": new_opt.quality_score},
    )
    db.commit()
    db.refresh(draft)
    return DraftSummaryResponse.model_validate(draft)


@router.post("/drafts/{draft_id}/mark", response_model=DraftSummaryResponse)
def mark_draft(
    draft_id: UUID,
    payload: DraftMarkRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    draft = get_owned_draft(db, user.user_id, draft_id)
    draft.status = payload.action
    log_activity(
        db,
        user_id=user.user_id,
        event_type=f"draft_{payload.action}",
        entity_type="draft",
        entity_id=draft.id,
        metadata={"post_id": str(draft.post_id)},
    )
    db.commit()
    db.refresh(draft)
    return DraftSummaryResponse.model_validate(draft)


@router.delete("/drafts/{draft_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_draft(
    draft_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    draft = get_owned_draft(db, user.user_id, draft_id)
    log_activity(
        db,
        user_id=user.user_id,
        event_type="draft_deleted",
        entity_type="draft",
        entity_id=draft.id,
    )
    db.delete(draft)
    db.commit()
    return None
