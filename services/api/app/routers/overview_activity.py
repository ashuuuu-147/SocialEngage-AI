"""Overview metrics, activity logs, monitoring jobs, profile, export, and account deletion."""

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.security import AuthenticatedUser, get_current_user
from app.db.session import get_db
from app.models.entities import (
    ActivityLog,
    CommentDraft,
    MonitoringJob,
    NotificationSettings,
    Post,
    Profile,
    StyleSample,
    TargetPost,
    TrackedTarget,
    UserPost,
    UserPreferences,
)
from app.schemas.api import (
    ActivityLogResponse,
    MonitoringJobResponse,
    OverviewResponse,
    ProfileResponse,
    ProfileUpdateRequest,
)
from app.services.ownership import log_activity

router = APIRouter(tags=["overview-activity-account"])


@router.get("/overview", response_model=OverviewResponse)
def get_overview(
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    targets = list(db.scalars(select(TrackedTarget).where(TrackedTarget.user_id == user.user_id)))
    tracked_profiles = len(targets)
    active_profiles = sum(1 for t in targets if t.status == "active")
    unsupported_profiles = sum(1 for t in targets if t.status in ("unsupported", "error"))

    last_checked = max((t.last_checked_at for t in targets if t.last_checked_at), default=None)

    owned_target_ids = select(TrackedTarget.id).where(TrackedTarget.user_id == user.user_id)
    linked_post_ids = select(TargetPost.post_id).where(TargetPost.target_id.in_(owned_target_ids))
    user_post_ids = select(UserPost.post_id).where(UserPost.user_id == user.user_id)
    new_posts_detected = (
        db.scalar(
            select(func.count(Post.id)).where(
                or_(
                    Post.submitted_by_user_id == user.user_id,
                    Post.id.in_(user_post_ids),
                    Post.id.in_(linked_post_ids),
                )
            )
        )
        or 0
    )

    drafts_awaiting_review = (
        db.scalar(
            select(func.count(CommentDraft.id)).where(
                CommentDraft.user_id == user.user_id,
                CommentDraft.status.in_(("pending", "edited")),
            )
        )
        or 0
    )
    drafts_approved_or_copied = (
        db.scalar(
            select(func.count(CommentDraft.id)).where(
                CommentDraft.user_id == user.user_id,
                CommentDraft.status.in_(("copied", "opened")),
            )
        )
        or 0
    )

    if any(t.status == "error" for t in targets):
        health = "degraded"
    elif active_profiles > 0:
        health = "healthy"
    else:
        health = "idle"

    recent = list(
        db.scalars(
            select(ActivityLog)
            .where(ActivityLog.user_id == user.user_id)
            .order_by(ActivityLog.created_at.desc())
            .limit(8)
        )
    )

    return OverviewResponse(
        tracked_profiles=tracked_profiles,
        active_profiles=active_profiles,
        unsupported_profiles=unsupported_profiles,
        new_posts_detected=int(new_posts_detected),
        drafts_awaiting_review=int(drafts_awaiting_review),
        drafts_approved_or_copied=int(drafts_approved_or_copied),
        monitoring_health=health,
        last_checked_at=last_checked,
        recent_activity=[ActivityLogResponse.model_validate(a) for a in recent],
    )


@router.get("/activity", response_model=list[ActivityLogResponse])
def list_activity(
    event_type: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(ActivityLog).where(ActivityLog.user_id == user.user_id)
    if event_type:
        stmt = stmt.where(ActivityLog.event_type == event_type)
    stmt = stmt.order_by(ActivityLog.created_at.desc()).limit(limit)
    rows = list(db.scalars(stmt))
    return [ActivityLogResponse.model_validate(r) for r in rows]


@router.get("/monitoring/jobs", response_model=list[MonitoringJobResponse])
def list_monitoring_jobs(
    limit: int = Query(default=30, ge=1, le=100),
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    owned_target_ids = select(TrackedTarget.id).where(TrackedTarget.user_id == user.user_id)
    stmt = (
        select(MonitoringJob)
        .where(MonitoringJob.target_id.in_(owned_target_ids))
        .order_by(MonitoringJob.created_at.desc())
        .limit(limit)
    )
    return [MonitoringJobResponse.model_validate(j) for j in db.scalars(stmt)]


@router.get("/profile", response_model=ProfileResponse)
def get_profile(
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.get(Profile, user.user_id)
    assert profile is not None
    return ProfileResponse.model_validate(profile)


@router.patch("/profile", response_model=ProfileResponse)
def update_profile(
    payload: ProfileUpdateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.get(Profile, user.user_id)
    assert profile is not None
    if payload.display_name is not None:
        profile.display_name = payload.display_name.strip()
    if payload.timezone is not None:
        profile.timezone = payload.timezone.strip()
    log_activity(db, user_id=user.user_id, event_type="profile_updated", entity_type="profile")
    db.commit()
    db.refresh(profile)
    return ProfileResponse.model_validate(profile)


@router.get("/account/export")
def export_account_data(
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.get(Profile, user.user_id)
    prefs = db.get(UserPreferences, user.user_id)
    notif = db.get(NotificationSettings, user.user_id)
    targets = list(db.scalars(select(TrackedTarget).where(TrackedTarget.user_id == user.user_id)))
    drafts = list(db.scalars(select(CommentDraft).where(CommentDraft.user_id == user.user_id)))
    samples = list(db.scalars(select(StyleSample).where(StyleSample.user_id == user.user_id)))
    logs = list(db.scalars(select(ActivityLog).where(ActivityLog.user_id == user.user_id)))

    return {
        "profile": {
            "id": str(profile.id) if profile else str(user.user_id),
            "display_name": profile.display_name if profile else None,
            "timezone": profile.timezone if profile else "Asia/Kolkata",
        },
        "preferences": {
            "tone": prefs.tone,
            "length": prefs.length,
            "language": prefs.language,
            "emoji_level": prefs.emoji_level,
            "relevance_threshold": float(prefs.relevance_threshold),
            "avoid_phrases": list(prefs.avoid_phrases or []),
            "preferred_topics": list(prefs.preferred_topics or []),
            "excluded_topics": list(prefs.excluded_topics or []),
        }
        if prefs
        else None,
        "notifications": {
            "telegram_enabled": notif.telegram_enabled,
            "daily_digest_enabled": notif.daily_digest_enabled,
            "digest_time": str(notif.digest_time),
        }
        if notif
        else None,
        "targets": [
            {
                "id": str(t.id),
                "platform": t.platform,
                "profile_url": t.profile_url,
                "display_name": t.display_name,
                "source_type": t.source_type,
                "status": t.status,
            }
            for t in targets
        ],
        "style_samples": [{"id": str(s.id), "sample_text": s.sample_text} for s in samples],
        "drafts": [
            {
                "id": str(d.id),
                "post_id": str(d.post_id),
                "draft_text": d.draft_text,
                "edited_text": d.edited_text,
                "status": d.status,
                "created_at": d.created_at.isoformat(),
            }
            for d in drafts
        ],
        "activity_logs": [
            {
                "id": str(a.id),
                "event_type": a.event_type,
                "created_at": a.created_at.isoformat(),
            }
            for a in logs
        ],
    }


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.get(Profile, user.user_id)
    if profile is not None:
        db.delete(profile)
        db.commit()
    return None
