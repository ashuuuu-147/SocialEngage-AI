"""Watchlist target management and source capability endpoints."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.core.security import AuthenticatedUser, get_current_user
from app.db.session import get_db
from app.models.entities import TrackedTarget
from app.schemas.api import (
    SourceCapabilityResponse,
    TargetCreateRequest,
    TargetResponse,
    TargetUpdateRequest,
)
from app.services.ownership import get_owned_target, log_activity
from app.source_adapters import SourceAdapterError, get_source_adapter
from app.workers.monitoring import run_monitoring_cycle

router = APIRouter(tags=["targets"])


def _to_target_response(target: TrackedTarget, settings: Settings) -> TargetResponse:
    adapter = get_source_adapter(target.source_type, settings)
    cap = adapter.check_access(target.platform)
    return TargetResponse(
        id=target.id,
        user_id=target.user_id,
        platform=target.platform,
        profile_url=target.profile_url,
        display_name=target.display_name,
        source_type=target.source_type,
        external_profile_id=target.external_profile_id,
        status=target.status,
        preferences=target.preferences or {},
        last_checked_at=target.last_checked_at,
        last_success_at=target.last_success_at,
        last_error_code=target.last_error_code,
        created_at=target.created_at,
        capability=SourceCapabilityResponse(
            source_type=cap.source_type,
            supported=cap.supported,
            reason=cap.reason,
            documentation_note=cap.documentation_note,
            requires_manual_fallback=cap.requires_manual_fallback,
        ),
    )


@router.get("/sources/capabilities")
def list_source_capabilities(
    settings: Settings = Depends(get_settings),
    _user: AuthenticatedUser = Depends(get_current_user),
):
    results = []
    for platform in ("linkedin", "instagram"):
        for source_type in ("official_api", "authorized_feed", "notification_import", "manual"):
            cap = get_source_adapter(source_type, settings).check_access(platform)
            results.append(
                {
                    "platform": platform,
                    "source_type": cap.source_type,
                    "supported": cap.supported,
                    "reason": cap.reason,
                    "documentation_note": cap.documentation_note,
                    "requires_manual_fallback": cap.requires_manual_fallback,
                }
            )
    return {"capabilities": results}


@router.get("/targets", response_model=list[TargetResponse])
def list_targets(
    platform: Optional[str] = Query(default=None),
    target_status: Optional[str] = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=25, ge=1, le=100),
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    stmt = select(TrackedTarget).where(TrackedTarget.user_id == user.user_id)
    if platform:
        stmt = stmt.where(TrackedTarget.platform == platform)
    if target_status:
        stmt = stmt.where(TrackedTarget.status == target_status)
    stmt = stmt.order_by(TrackedTarget.created_at.desc()).offset((page - 1) * limit).limit(limit)
    rows = list(db.scalars(stmt))
    return [_to_target_response(row, settings) for row in rows]


@router.post("/targets", response_model=TargetResponse, status_code=status.HTTP_201_CREATED)
def create_target(
    payload: TargetCreateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    try:
        adapter = get_source_adapter(payload.source_type, settings)
        canonical_profile = adapter.validate_target(payload.platform, payload.profile_url)
    except SourceAdapterError as exc:
        raise AppError(exc.code, exc.message, status.HTTP_400_BAD_REQUEST) from exc

    existing = db.scalar(
        select(TrackedTarget).where(
            TrackedTarget.user_id == user.user_id,
            TrackedTarget.platform == payload.platform,
            TrackedTarget.profile_url == canonical_profile,
        )
    )
    if existing is not None:
        raise AppError("TARGET_ALREADY_EXISTS", "This profile is already in your watchlist.", 409)

    cap = adapter.check_access(payload.platform)
    initial_status = "active" if cap.supported else "unsupported"
    last_error = None if cap.supported else "SOURCE_UNAVAILABLE"

    target = TrackedTarget(
        user_id=user.user_id,
        platform=payload.platform,
        profile_url=canonical_profile,
        display_name=payload.display_name or canonical_profile.rstrip("/").split("/")[-1],
        source_type=payload.source_type,
        external_profile_id=payload.external_profile_id,
        status=initial_status,
        preferences=payload.preferences,
        last_error_code=last_error,
    )
    db.add(target)
    db.flush()
    log_activity(
        db,
        user_id=user.user_id,
        event_type="target_created",
        entity_type="target",
        entity_id=target.id,
        metadata={"platform": target.platform, "source_type": target.source_type, "status": target.status},
    )
    db.commit()
    db.refresh(target)
    return _to_target_response(target, settings)


@router.patch("/targets/{target_id}", response_model=TargetResponse)
def update_target(
    target_id: UUID,
    payload: TargetUpdateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    target = get_owned_target(db, user.user_id, target_id)
    if payload.display_name is not None:
        target.display_name = payload.display_name
    if payload.preferences is not None:
        target.preferences = payload.preferences
    if payload.source_type is not None:
        target.source_type = payload.source_type
        cap = get_source_adapter(payload.source_type, settings).check_access(target.platform)
        target.status = "active" if cap.supported else "unsupported"
        target.last_error_code = None if cap.supported else "SOURCE_UNAVAILABLE"
    if payload.status is not None:
        cap = get_source_adapter(target.source_type, settings).check_access(target.platform)
        if payload.status == "active" and not cap.supported:
            target.status = "unsupported"
            target.last_error_code = "SOURCE_UNAVAILABLE"
        else:
            target.status = payload.status
            if payload.status == "active":
                target.last_error_code = None

    log_activity(
        db,
        user_id=user.user_id,
        event_type="target_updated",
        entity_type="target",
        entity_id=target.id,
        metadata={"status": target.status, "source_type": target.source_type},
    )
    db.commit()
    db.refresh(target)
    return _to_target_response(target, settings)


@router.delete("/targets/{target_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_target(
    target_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target = get_owned_target(db, user.user_id, target_id)
    log_activity(
        db,
        user_id=user.user_id,
        event_type="target_deleted",
        entity_type="target",
        entity_id=target.id,
        metadata={"platform": target.platform, "display_name": target.display_name},
    )
    db.delete(target)
    db.commit()
    return None


@router.post("/targets/{target_id}/check")
async def trigger_target_check(
    target_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    target = get_owned_target(db, user.user_id, target_id)
    if target.source_type == "manual":
        return {
            "status": "manual_only",
            "message": "Manual targets do not auto-poll. Use 'Submit Post URL' to ingest a post.",
        }
    summary = await run_monitoring_cycle(db, settings, target_id=target.id, force=True)
    return {"status": "completed", "summary": summary}
