"""Authentication, Supabase JWT verification, internal job HMAC, and rate limiting."""

import hashlib
import hmac
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock
from typing import Optional

import jwt
from fastapi import Depends, Header, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.db.session import get_db
from app.models.entities import NotificationSettings, Profile, UserPreferences

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class AuthenticatedUser:
    user_id: uuid.UUID
    email: str
    display_name: str
    is_dev_bypass: bool = False


class InMemoryRateLimiter:
    """Simple sliding-window rate limiter per key."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str, max_requests: int, window_seconds: int) -> None:
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            dq = self._hits[key]
            while dq and dq[0] < cutoff:
                dq.popleft()
            if len(dq) >= max_requests:
                raise AppError(
                    code="RATE_LIMIT_EXCEEDED",
                    message="Too many requests. Please slow down and try again shortly.",
                    status_code=status.HTTP_429_RATE_LIMIT_EXCEEDED
                    if hasattr(status, "HTTP_429_RATE_LIMIT_EXCEEDED")
                    else 429,
                )
            dq.append(now)


rate_limiter = InMemoryRateLimiter()


def ensure_user_bootstrap(
    db: Session,
    user_id: uuid.UUID,
    display_name: Optional[str] = None,
) -> Profile:
    """Ensure profile, preferences, and notification settings rows exist for an authenticated user."""
    profile = db.get(Profile, user_id)
    if profile is None:
        profile = Profile(
            id=user_id,
            display_name=display_name or "SocialEngage User",
            timezone="Asia/Kolkata",
        )
        db.add(profile)
        db.flush()

    if db.get(UserPreferences, user_id) is None:
        db.add(UserPreferences(user_id=user_id))
    if db.get(NotificationSettings, user_id) is None:
        db.add(NotificationSettings(user_id=user_id))
    db.commit()
    db.refresh(profile)
    return profile


def _decode_supabase_jwt(token: str, settings: Settings) -> dict:
    """Verify Supabase JWT via HS256 secret or Supabase JWKS (RS256/ES256)."""
    try:
        header = jwt.get_unverified_header(token)
        alg = str(header.get("alg") or "HS256").upper()
    except jwt.InvalidTokenError as exc:
        raise AppError(
            code="INVALID_TOKEN",
            message="Invalid authentication token header.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        ) from exc

    if alg.startswith("HS"):
        if not settings.supabase_jwt_secret:
            raise AppError(
                code="AUTH_NOT_CONFIGURED",
                message="SUPABASE_JWT_SECRET is required to verify HS256 tokens.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        try:
            return jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                options={"verify_aud": False},
            )
        except jwt.ExpiredSignatureError as exc:
            raise AppError(
                code="TOKEN_EXPIRED",
                message="Authentication token has expired.",
                status_code=status.HTTP_401_UNAUTHORIZED,
            ) from exc
        except jwt.InvalidTokenError as exc:
            raise AppError(
                code="INVALID_TOKEN",
                message="Invalid authentication token.",
                status_code=status.HTTP_401_UNAUTHORIZED,
            ) from exc

    if not settings.supabase_url:
        raise AppError(
            code="AUTH_NOT_CONFIGURED",
            message="SUPABASE_URL is required to verify asymmetric JWKS tokens.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    jwks_url = f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
    try:
        jwk_client = jwt.PyJWKClient(jwks_url, cache_keys=True)
        signing_key = jwk_client.get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "ES256"],
            options={"verify_aud": False},
        )
    except jwt.ExpiredSignatureError as exc:
        raise AppError(
            code="TOKEN_EXPIRED",
            message="Authentication token has expired.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise AppError(
            code="INVALID_TOKEN",
            message="Invalid authentication token.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        ) from exc


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    x_dev_user_id: Optional[str] = Header(default=None, alias="X-Dev-User-Id"),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthenticatedUser:
    # Real JWT takes precedence when provided
    if credentials and credentials.credentials:
        token = credentials.credentials.strip()
        # Allow explicit dev token in dev_auth_bypass mode when formatted as "dev:<uuid>"
        if settings.dev_auth_bypass and settings.app_env != "production" and token.startswith("dev:"):
            raw_uid = token.split(":", 1)[1].strip() or settings.dev_user_id
            try:
                uid = uuid.UUID(raw_uid)
            except ValueError as exc:
                raise AppError("INVALID_TOKEN", "Invalid dev user UUID.", 401) from exc
            profile = ensure_user_bootstrap(db, uid, "Demo User")
            return AuthenticatedUser(
                user_id=uid,
                email=settings.dev_user_email,
                display_name=profile.display_name or "Demo User",
                is_dev_bypass=True,
            )

        payload = _decode_supabase_jwt(token, settings)
        sub = payload.get("sub")
        if not sub:
            raise AppError("INVALID_TOKEN", "Token missing subject claim.", 401)
        try:
            uid = uuid.UUID(str(sub))
        except ValueError as exc:
            raise AppError("INVALID_TOKEN", "Token subject is not a valid UUID.", 401) from exc
        email = str(payload.get("email") or "")
        meta = payload.get("user_metadata") or {}
        display_name = meta.get("display_name") or (email.split("@")[0] if email else "User")
        profile = ensure_user_bootstrap(db, uid, display_name)
        return AuthenticatedUser(
            user_id=uid,
            email=email,
            display_name=profile.display_name or display_name,
            is_dev_bypass=False,
        )

    # Local development bypass when explicitly enabled and non-production
    if settings.dev_auth_bypass and settings.app_env != "production":
        raw_uid = x_dev_user_id or settings.dev_user_id
        try:
            uid = uuid.UUID(raw_uid)
        except ValueError as exc:
            raise AppError("INVALID_DEV_USER", "Invalid X-Dev-User-Id header.", 400) from exc
        profile = ensure_user_bootstrap(db, uid, "Demo User")
        return AuthenticatedUser(
            user_id=uid,
            email=settings.dev_user_email,
            display_name=profile.display_name or "Demo User",
            is_dev_bypass=True,
        )

    raise AppError(
        code="UNAUTHENTICATED",
        message="Authentication credentials were not provided.",
        status_code=status.HTTP_401_UNAUTHORIZED,
    )


def compute_internal_signature(secret: str, timestamp: str, body: bytes) -> str:
    msg = f"{timestamp}.".encode("utf-8") + body
    return hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()


async def verify_internal_job_auth(
    request: Request,
    authorization: Optional[str] = Header(default=None),
    x_internal_signature: Optional[str] = Header(default=None, alias="X-Internal-Job-Signature"),
    x_internal_timestamp: Optional[str] = Header(default=None, alias="X-Internal-Job-Timestamp"),
    settings: Settings = Depends(get_settings),
) -> None:
    """Verify signed HMAC or bearer secret for internal cloud worker endpoints."""
    secret = settings.internal_job_secret
    if not secret:
        raise AppError("INTERNAL_AUTH_NOT_CONFIGURED", "Internal job secret is not configured.", 500)

    if x_internal_signature and x_internal_timestamp:
        try:
            ts = int(x_internal_timestamp)
        except ValueError as exc:
            raise AppError("INVALID_SIGNATURE", "Invalid internal job timestamp.", 401) from exc
        if abs(int(time.time()) - ts) > 300:
            raise AppError("SIGNATURE_EXPIRED", "Internal job signature expired.", 401)
        body = await request.body()
        expected = compute_internal_signature(secret, x_internal_timestamp, body)
        if hmac.compare_digest(expected, x_internal_signature):
            return
        raise AppError("INVALID_SIGNATURE", "Invalid internal job signature.", 401)

    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
        if hmac.compare_digest(token, secret):
            return

    raise AppError(
        code="UNAUTHORIZED_INTERNAL_JOB",
        message="Missing or invalid internal worker authorization.",
        status_code=status.HTTP_401_UNAUTHORIZED,
    )
