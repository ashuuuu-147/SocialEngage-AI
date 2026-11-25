"""Telegram verification, notification settings, test, and disconnect endpoints."""

import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.core.security import AuthenticatedUser, get_current_user
from app.db.session import get_db
from app.models.entities import NotificationSettings
from app.notifications.telegram import TelegramNotifier
from app.schemas.api import (
    NotificationSettingsResponse,
    NotificationSettingsUpdateRequest,
    TelegramConnectResponse,
    TelegramVerifyRequest,
)
from app.services.ownership import log_activity

router = APIRouter(tags=["notifications"])


def _mask_chat_id(chat_id: str | None) -> str | None:
    if not chat_id:
        return None
    if len(chat_id) <= 4:
        return "****"
    return f"***{chat_id[-4:]}"


def _serialize_notif(row: NotificationSettings) -> NotificationSettingsResponse:
    return NotificationSettingsResponse(
        user_id=row.user_id,
        telegram_enabled=row.telegram_enabled,
        telegram_connected=bool(row.telegram_chat_id),
        telegram_chat_id_masked=_mask_chat_id(row.telegram_chat_id),
        daily_digest_enabled=row.daily_digest_enabled,
        digest_time=row.digest_time,
        updated_at=row.updated_at,
    )


@router.get("/notifications/settings", response_model=NotificationSettingsResponse)
def get_notification_settings(
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = db.get(NotificationSettings, user.user_id)
    if row is None:
        row = NotificationSettings(user_id=user.user_id)
        db.add(row)
        db.commit()
        db.refresh(row)
    return _serialize_notif(row)


@router.put("/notifications/settings", response_model=NotificationSettingsResponse)
def update_notification_settings(
    payload: NotificationSettingsUpdateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = db.get(NotificationSettings, user.user_id)
    if row is None:
        row = NotificationSettings(user_id=user.user_id)
        db.add(row)
        db.flush()

    if payload.telegram_enabled is not None:
        if payload.telegram_enabled and not row.telegram_chat_id:
            raise AppError(
                "TELEGRAM_NOT_VERIFIED",
                "Verify your Telegram chat before enabling Telegram notifications.",
                400,
            )
        row.telegram_enabled = payload.telegram_enabled
    if payload.daily_digest_enabled is not None:
        row.daily_digest_enabled = payload.daily_digest_enabled
    if payload.digest_time is not None:
        row.digest_time = payload.digest_time

    log_activity(
        db,
        user_id=user.user_id,
        event_type="notification_settings_updated",
        entity_type="notification",
    )
    db.commit()
    db.refresh(row)
    return _serialize_notif(row)


@router.post("/notifications/telegram/connect", response_model=TelegramConnectResponse)
def initiate_telegram_connect(
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    row = db.get(NotificationSettings, user.user_id)
    if row is None:
        row = NotificationSettings(user_id=user.user_id)
        db.add(row)
        db.flush()

    code = f"SE-{secrets.token_urlsafe(12)}"
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
    row.telegram_verification_code = code
    row.telegram_verification_expires_at = expires_at

    log_activity(
        db,
        user_id=user.user_id,
        event_type="telegram_connect_initiated",
        entity_type="notification",
    )
    db.commit()

    notifier = TelegramNotifier(settings)
    deep_link = notifier.build_deep_link(code)
    instructions = (
        f"Open the bot link and press Start, or verify code '{code}' within 15 minutes."
        if deep_link
        else f"Configure TELEGRAM_BOT_USERNAME on the server, or verify code '{code}' via bot webhook/local verification."
    )
    return TelegramConnectResponse(
        verification_code=code,
        expires_at=expires_at,
        bot_username=settings.telegram_bot_username or None,
        deep_link_url=deep_link,
        instructions=instructions,
    )


@router.post("/notifications/telegram/verify", response_model=NotificationSettingsResponse)
def verify_telegram_connection(
    payload: TelegramVerifyRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Complete one-time verification code exchange; rejects arbitrary unverified chat IDs."""
    row = db.get(NotificationSettings, user.user_id)
    if (
        row is None
        or not row.telegram_verification_code
        or row.telegram_verification_code != payload.verification_code
    ):
        raise AppError("INVALID_VERIFICATION_CODE", "Invalid Telegram verification code.", 400)

    now = datetime.now(timezone.utc)
    expires = row.telegram_verification_expires_at
    if expires is not None:
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < now:
            raise AppError("VERIFICATION_CODE_EXPIRED", "Verification code has expired.", 400)

    row.telegram_chat_id = payload.chat_id.strip()
    row.telegram_enabled = True
    row.telegram_verification_code = None
    row.telegram_verification_expires_at = None

    log_activity(
        db,
        user_id=user.user_id,
        event_type="telegram_connected",
        entity_type="notification",
    )
    db.commit()
    db.refresh(row)
    return _serialize_notif(row)


@router.post("/notifications/telegram/disconnect", response_model=NotificationSettingsResponse)
def disconnect_telegram(
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = db.get(NotificationSettings, user.user_id)
    if row is None:
        row = NotificationSettings(user_id=user.user_id)
        db.add(row)
    row.telegram_chat_id = None
    row.telegram_enabled = False
    row.telegram_verification_code = None
    row.telegram_verification_expires_at = None

    log_activity(
        db,
        user_id=user.user_id,
        event_type="telegram_disconnected",
        entity_type="notification",
    )
    db.commit()
    db.refresh(row)
    return _serialize_notif(row)


@router.post("/notifications/test")
async def send_test_notification(
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    row = db.get(NotificationSettings, user.user_id)
    if row is None or not row.telegram_chat_id:
        raise AppError(
            "TELEGRAM_NOT_CONNECTED",
            "Connect and verify a Telegram chat before sending a test message.",
            400,
        )

    notifier = TelegramNotifier(settings)
    result = await notifier.send_message(
        row.telegram_chat_id,
        "<b>SocialEngage AI</b>\nTest notification succeeded. New drafts will appear here for review.",
    )
    log_activity(
        db,
        user_id=user.user_id,
        event_type="telegram_test_sent" if result.delivered else "telegram_test_failed",
        entity_type="notification",
        metadata={"mode": result.mode, "detail": result.detail},
    )
    db.commit()
    return {"delivered": result.delivered, "mode": result.mode, "detail": result.detail}


@router.post("/notifications/telegram/webhook")
async def telegram_bot_webhook(
    update: dict[str, Any],
    x_telegram_bot_api_secret_token: Optional[str] = Header(
        default=None, alias="X-Telegram-Bot-Api-Secret-Token"
    ),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Receive Telegram Bot webhook updates to complete /start <code> deep-link verification."""
    if not settings.telegram_webhook_secret:
        raise AppError(
            "WEBHOOK_NOT_CONFIGURED",
            "TELEGRAM_WEBHOOK_SECRET is not configured on the server.",
            500,
        )
    if not x_telegram_bot_api_secret_token or not hmac.compare_digest(
        x_telegram_bot_api_secret_token, settings.telegram_webhook_secret
    ):
        raise AppError("UNAUTHORIZED_WEBHOOK", "Invalid Telegram webhook secret token.", 401)

    message = update.get("message") or {}
    text = str(message.get("text") or "").strip()
    chat = message.get("chat") or {}
    chat_id = chat.get("id")

    if not text.startswith("/start") or chat_id is None:
        return {"ok": True, "handled": False}

    parts = text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        return {"ok": True, "handled": False}

    code = parts[1].strip()
    row = db.scalar(
        select(NotificationSettings).where(NotificationSettings.telegram_verification_code == code)
    )
    notifier = TelegramNotifier(settings)

    if row is None:
        await notifier.send_message(
            str(chat_id),
            "This verification link is invalid or already used. Please generate a new code in SocialEngage AI Settings.",
        )
        return {"ok": True, "handled": True, "verified": False}

    now = datetime.now(timezone.utc)
    expires = row.telegram_verification_expires_at
    if expires is not None:
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < now:
            await notifier.send_message(
                str(chat_id),
                "This verification code has expired. Please generate a new code in SocialEngage AI Settings.",
            )
            return {"ok": True, "handled": True, "verified": False}

    row.telegram_chat_id = str(chat_id)
    row.telegram_enabled = True
    row.telegram_verification_code = None
    row.telegram_verification_expires_at = None
    log_activity(
        db,
        user_id=row.user_id,
        event_type="telegram_connected_webhook",
        entity_type="notification",
    )
    db.commit()

    await notifier.send_message(
        str(chat_id),
        "<b>Connected!</b> Your Telegram chat is now linked to SocialEngage AI for draft review alerts.",
    )
    return {"ok": True, "handled": True, "verified": True}
