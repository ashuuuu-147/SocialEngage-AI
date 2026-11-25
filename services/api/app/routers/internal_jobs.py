"""Protected internal cloud worker endpoints (API_SPEC.md)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.core.security import verify_internal_job_auth
from app.db.session import get_db
from app.models.entities import Post
from app.schemas.api import InternalMonitorJobRequest, InternalProcessPostRequest
from app.workers.monitoring import (
    process_post_for_user,
    run_daily_digest_cycle,
    run_monitoring_cycle,
)

router = APIRouter(
    prefix="/internal/jobs",
    tags=["internal-jobs"],
    dependencies=[Depends(verify_internal_job_auth)],
)


@router.post("/monitor")
async def internal_monitor_job(
    payload: InternalMonitorJobRequest = InternalMonitorJobRequest(),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    summary = await run_monitoring_cycle(
        db,
        settings,
        target_id=payload.target_id,
        force=payload.force,
    )
    return {"status": "ok", "summary": summary}


@router.post("/process-post")
async def internal_process_post_job(
    payload: InternalProcessPostRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    post = db.get(Post, payload.post_id)
    if post is None:
        raise AppError("POST_NOT_FOUND", "Post not found.", 404)

    drafts = await process_post_for_user(
        db,
        post=post,
        user_id=payload.user_id,
        settings=settings,
        variants=payload.variants,
        notify_telegram=payload.notify_telegram,
    )
    return {"status": "ok", "drafts_created": len(drafts)}


@router.post("/daily-digest")
async def internal_daily_digest_job(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    summary = await run_daily_digest_cycle(db, settings)
    return {"status": "ok", "summary": summary}
