"""Telegram Bot API client and secure verification link helpers."""

import html
import logging
from dataclasses import dataclass
from typing import Optional

import httpx

from app.core.config import Settings

logger = logging.getLogger("socialengage.telegram")


@dataclass
class TelegramDeliveryResult:
    delivered: bool
    mode: str  # "telegram_api" | "mock_local" | "disabled"
    detail: str


class TelegramNotifier:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def is_configured(self) -> bool:
        return bool(self.settings.telegram_bot_token)

    def build_deep_link(self, verification_code: str) -> Optional[str]:
        if not self.settings.telegram_bot_username:
            return None
        username = self.settings.telegram_bot_username.lstrip("@")
        return f"https://t.me/{username}?start={verification_code}"

    async def send_message(self, chat_id: str, text: str) -> TelegramDeliveryResult:
        if not self.is_configured:
            if self.settings.enable_mock_sources:
                logger.info("Telegram mock delivery to masked chat_id=%s", chat_id[-4:] if chat_id else "none")
                return TelegramDeliveryResult(
                    delivered=True,
                    mode="mock_local",
                    detail="TELEGRAM_BOT_TOKEN not configured; recorded simulated local delivery.",
                )
            return TelegramDeliveryResult(
                delivered=False,
                mode="disabled",
                detail="TELEGRAM_BOT_TOKEN is not configured on the server.",
            )

        url = f"https://api.telegram.org/bot{self.settings.telegram_bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                resp = await client.post(url, json=payload)
            if resp.status_code >= 400:
                return TelegramDeliveryResult(
                    delivered=False,
                    mode="telegram_api",
                    detail=f"Telegram API error HTTP {resp.status_code}",
                )
            return TelegramDeliveryResult(
                delivered=True,
                mode="telegram_api",
                detail="Delivered via Telegram Bot API.",
            )
        except httpx.RequestError as exc:
            return TelegramDeliveryResult(
                delivered=False,
                mode="telegram_api",
                detail=f"Telegram network error: {exc}",
            )

    def format_draft_notification(
        self,
        *,
        platform: str,
        author_name: str,
        post_preview: str,
        draft_text: str,
        post_url: str,
        draft_id: str,
    ) -> str:
        dashboard_link = f"{self.settings.web_app_url.rstrip('/')}/drafts?highlight={draft_id}"
        safe_author = html.escape(author_name or "Watched Profile")
        safe_preview = html.escape((post_preview or "")[:160])
        safe_draft = html.escape((draft_text or "")[:350])
        safe_post_url = html.escape(post_url)
        safe_dash = html.escape(dashboard_link)

        return (
            f"<b>New {html.escape(platform.title())} Draft Ready</b>\n"
            f"<b>Author:</b> {safe_author}\n"
            f"<b>Post:</b> {safe_preview}...\n\n"
            f"<b>Suggested Draft (review before posting):</b>\n"
            f"<code>{safe_draft}</code>\n\n"
            f'<a href="{safe_post_url}">Open Post</a> | '
            f'<a href="{safe_dash}">Review in Dashboard</a>'
        )

    def format_daily_digest(
        self,
        *,
        posts_count: int,
        drafts_pending: int,
        skipped_count: int,
    ) -> str:
        dashboard_link = f"{self.settings.web_app_url.rstrip('/')}/drafts"
        return (
            f"<b>SocialEngage AI — Daily Digest</b>\n"
            f"• Posts detected (24h): <b>{posts_count}</b>\n"
            f"• Drafts awaiting review: <b>{drafts_pending}</b>\n"
            f"• Skipped items: <b>{skipped_count}</b>\n\n"
            f'<a href="{html.escape(dashboard_link)}">Open Review Queue</a>'
        )
