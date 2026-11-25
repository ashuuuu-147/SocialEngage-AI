"""User preferences and personal style sample endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import AuthenticatedUser, get_current_user
from app.db.session import get_db
from app.models.entities import StyleSample, UserPreferences
from app.schemas.api import (
    PreferencesResponse,
    PreferencesUpdateRequest,
    StyleSampleCreateRequest,
    StyleSampleResponse,
)
from app.services.ownership import get_owned_style_sample, log_activity

router = APIRouter(tags=["preferences"])


@router.get("/preferences", response_model=PreferencesResponse)
def get_preferences(
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    prefs = db.get(UserPreferences, user.user_id)
    if prefs is None:
        prefs = UserPreferences(user_id=user.user_id)
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
    return PreferencesResponse(
        user_id=prefs.user_id,
        tone=prefs.tone,
        length=prefs.length,
        language=prefs.language,
        emoji_level=prefs.emoji_level,
        relevance_threshold=float(prefs.relevance_threshold),
        avoid_phrases=list(prefs.avoid_phrases or []),
        preferred_topics=list(prefs.preferred_topics or []),
        excluded_topics=list(prefs.excluded_topics or []),
        monitoring_interval_minutes=prefs.monitoring_interval_minutes,
        data_retention_days=prefs.data_retention_days,
        updated_at=prefs.updated_at,
    )


@router.put("/preferences", response_model=PreferencesResponse)
def update_preferences(
    payload: PreferencesUpdateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    prefs = db.get(UserPreferences, user.user_id)
    if prefs is None:
        prefs = UserPreferences(user_id=user.user_id)
        db.add(prefs)
        db.flush()

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(prefs, field, value)

    log_activity(
        db,
        user_id=user.user_id,
        event_type="preferences_updated",
        entity_type="preferences",
        metadata={"fields": list(update_data.keys())},
    )
    db.commit()
    db.refresh(prefs)
    return get_preferences(user=user, db=db)


@router.get("/style-samples", response_model=list[StyleSampleResponse])
def list_style_samples(
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = list(
        db.scalars(
            select(StyleSample)
            .where(StyleSample.user_id == user.user_id)
            .order_by(StyleSample.created_at.desc())
        )
    )
    return [StyleSampleResponse.model_validate(r) for r in rows]


@router.post("/style-samples", response_model=StyleSampleResponse, status_code=status.HTTP_201_CREATED)
def create_style_sample(
    payload: StyleSampleCreateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sample = StyleSample(user_id=user.user_id, sample_text=payload.sample_text.strip())
    db.add(sample)
    db.flush()
    log_activity(
        db,
        user_id=user.user_id,
        event_type="style_sample_added",
        entity_type="style_sample",
        entity_id=sample.id,
    )
    db.commit()
    db.refresh(sample)
    return StyleSampleResponse.model_validate(sample)


@router.delete("/style-samples/{sample_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_style_sample(
    sample_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sample = get_owned_style_sample(db, user.user_id, sample_id)
    log_activity(
        db,
        user_id=user.user_id,
        event_type="style_sample_deleted",
        entity_type="style_sample",
        entity_id=sample.id,
    )
    db.delete(sample)
    db.commit()
    return None
