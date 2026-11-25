"""FastAPI application entrypoint for SocialEngage AI."""

import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Settings, get_settings
from app.core.errors import (
    AppError,
    app_error_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_error_handler,
)
from app.core.logging import configure_logging
from app.db.session import init_db
from app.routers import (
    drafts,
    internal_jobs,
    notifications,
    overview_activity,
    posts,
    preferences,
    targets,
)

settings = get_settings()
logger = configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    logger.info("SocialEngage AI API initialized in env=%s", settings.app_env)
    yield


app = FastAPI(
    title="SocialEngage AI API",
    version="1.0.0",
    description="Cloud-first AI social engagement assistant REST API v1.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def attach_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-Id"] = request_id
    return response


app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)


@app.get("/health", tags=["health"])
def health_check(app_settings: Settings = Depends(get_settings)):
    return {
        "status": "ok",
        "service": "socialengage-api",
        "env": app_settings.app_env,
        "ai_provider": app_settings.ai_provider,
        "dev_auth_bypass": app_settings.dev_auth_bypass and app_settings.app_env != "production",
    }


API_PREFIX = "/api/v1"
app.include_router(targets.router, prefix=API_PREFIX)
app.include_router(posts.router, prefix=API_PREFIX)
app.include_router(drafts.router, prefix=API_PREFIX)
app.include_router(preferences.router, prefix=API_PREFIX)
app.include_router(notifications.router, prefix=API_PREFIX)
app.include_router(overview_activity.router, prefix=API_PREFIX)
app.include_router(internal_jobs.router, prefix=API_PREFIX)
