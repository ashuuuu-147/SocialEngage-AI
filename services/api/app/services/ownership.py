"""Shared ownership verification and activity logging helpers."""

from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.entities import ActivityLog, CommentDraft, Post, StyleSample, TargetPost, TrackedTarget, UserPost


def log_activity(
    db: Session,
    *,
    user_id: UUID,
    event_type: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[UUID] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> None:
    db.add(
        ActivityLog(
            user_id=user_id,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata_json=metadata or {},
        )
    )


def get_owned_target(db: Session, user_id: UUID, target_id: UUID) -> TrackedTarget:
    target = db.get(TrackedTarget, target_id)
    if target is None:
        raise AppError("TARGET_NOT_FOUND", "Target was not found.", 404)
    if target.user_id != user_id:
        raise AppError("UNAUTHORIZED", "You do not have permission to access this target.", 403)
    return target


def get_owned_post(db: Session, user_id: UUID, post_id: UUID) -> Post:
    post = db.get(Post, post_id)
    if post is None:
        raise AppError("POST_NOT_FOUND", "Post was not found.", 404)
    if post.submitted_by_user_id == user_id:
        return post
    user_link = db.scalar(
        select(UserPost.id).where(UserPost.post_id == post_id, UserPost.user_id == user_id)
    )
    if user_link is not None:
        return post
    linked = db.scalar(
        select(TargetPost.id)
        .join(TrackedTarget, TrackedTarget.id == TargetPost.target_id)
        .where(TargetPost.post_id == post_id, TrackedTarget.user_id == user_id)
    )
    if linked is not None:
        return post
    # Also allow if user already owns a draft for this post
    has_draft = db.scalar(
        select(CommentDraft.id).where(
            CommentDraft.post_id == post_id,
            CommentDraft.user_id == user_id,
        )
    )
    if has_draft is not None:
        return post
    raise AppError("UNAUTHORIZED", "You do not have permission to access this post.", 403)


def get_owned_draft(db: Session, user_id: UUID, draft_id: UUID) -> CommentDraft:
    draft = db.get(CommentDraft, draft_id)
    if draft is None:
        raise AppError("DRAFT_NOT_FOUND", "Draft was not found.", 404)
    if draft.user_id != user_id:
        raise AppError("UNAUTHORIZED", "You do not have permission to access this draft.", 403)
    return draft


def get_owned_style_sample(db: Session, user_id: UUID, sample_id: UUID) -> StyleSample:
    sample = db.get(StyleSample, sample_id)
    if sample is None:
        raise AppError("STYLE_SAMPLE_NOT_FOUND", "Style sample was not found.", 404)
    if sample.user_id != user_id:
        raise AppError("UNAUTHORIZED", "You do not have permission to delete this style sample.", 403)
    return sample
