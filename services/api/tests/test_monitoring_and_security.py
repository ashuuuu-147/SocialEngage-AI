"""Security, SSRF, Telegram verification, internal HMAC worker auth, monitoring, and SQL migration tests."""

import json
import re
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import func, select

from app.core.security import compute_internal_signature
from app.models.entities import (
    ActivityLog,
    CommentDraft,
    MonitoringJob,
    NotificationSettings,
    Post,
    Profile,
    TrackedTarget,
)
from app.source_adapters import AuthorizedFeedAdapter, SourceAdapterError, validate_public_http_url
from app.workers.monitoring import run_monitoring_cycle


@pytest.mark.parametrize(
    "unsafe_url",
    [
        "http://127.0.0.1/feed",
        "http://localhost:8000",
        "http://169.254.169.254/latest/meta-data",
        "http://10.0.0.5/rss",
        "http://10.0.0.1/rss",
        "http://[::1]/feed",
        "http://internal.local/rss",
        "ftp://example.com/feed.xml",
    ],
)
def test_ssrf_validation_blocks_internal_and_non_http_urls(unsafe_url: str):
    with pytest.raises(SourceAdapterError) as exc_info:
        validate_public_http_url(unsafe_url)
    assert exc_info.value.code in ("UNSAFE_URL", "INVALID_URL")


@pytest.mark.asyncio
async def test_authorized_feed_adapter_enforces_ssrf_before_http(test_settings):
    adapter = AuthorizedFeedAdapter(test_settings)
    with patch("app.source_adapters.adapters.httpx.AsyncClient") as mock_client:
        for url in (
            "http://127.0.0.1/feed",
            "http://localhost:8000",
            "http://169.254.169.254/latest/meta-data",
            "http://10.0.0.5/rss",
        ):
            with pytest.raises(SourceAdapterError) as exc_info:
                await adapter.fetch_recent_posts(
                    platform="linkedin",
                    profile_url="https://www.linkedin.com/in/example",
                    preferences={"feed_url": url},
                )
            assert exc_info.value.code == "UNSAFE_URL"
        mock_client.assert_not_called()


def test_telegram_connect_verify_mask_test_and_disconnect(
    client, db_session, user_a_id, user_a_headers
):
    # Cannot enable telegram before verification
    early_enable = client.put(
        "/api/v1/notifications/settings",
        headers=user_a_headers,
        json={"telegram_enabled": True},
    )
    assert early_enable.status_code == 400
    assert early_enable.json()["error"]["code"] == "TELEGRAM_NOT_VERIFIED"

    # Initiate connect
    connect_resp = client.post("/api/v1/notifications/telegram/connect", headers=user_a_headers)
    assert connect_resp.status_code == 200
    conn_data = connect_resp.json()
    code = conn_data["verification_code"]
    assert code.startswith("SE-")
    assert conn_data["deep_link_url"] == f"https://t.me/SocialEngageTestBot?start={code}"

    # Invalid code rejected
    bad_code = client.post(
        "/api/v1/notifications/telegram/verify",
        headers=user_a_headers,
        json={"verification_code": "SE-wrong-code", "chat_id": "987654321"},
    )
    assert bad_code.status_code == 400
    assert bad_code.json()["error"]["code"] == "INVALID_VERIFICATION_CODE"

    # Expired code rejected
    notif_row = db_session.get(NotificationSettings, user_a_id)
    assert notif_row is not None
    notif_row.telegram_verification_expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db_session.commit()

    expired_resp = client.post(
        "/api/v1/notifications/telegram/verify",
        headers=user_a_headers,
        json={"verification_code": code, "chat_id": "987654321"},
    )
    assert expired_resp.status_code == 400
    assert expired_resp.json()["error"]["code"] == "VERIFICATION_CODE_EXPIRED"

    # Re-issue fresh code and verify successfully
    fresh_code = client.post(
        "/api/v1/notifications/telegram/connect", headers=user_a_headers
    ).json()["verification_code"]

    verify_resp = client.post(
        "/api/v1/notifications/telegram/verify",
        headers=user_a_headers,
        json={"verification_code": fresh_code, "chat_id": "987654321"},
    )
    assert verify_resp.status_code == 200
    v_data = verify_resp.json()
    assert v_data["telegram_connected"] is True
    assert v_data["telegram_enabled"] is True
    assert v_data["telegram_chat_id_masked"] == "***4321"
    assert "987654321" not in json.dumps(v_data)

    # One-time code cannot be reused
    reuse_resp = client.post(
        "/api/v1/notifications/telegram/verify",
        headers=user_a_headers,
        json={"verification_code": fresh_code, "chat_id": "987654321"},
    )
    assert reuse_resp.status_code == 400
    assert reuse_resp.json()["error"]["code"] == "INVALID_VERIFICATION_CODE"

    # Send test notification (local mock delivery)
    test_resp = client.post("/api/v1/notifications/test", headers=user_a_headers)
    assert test_resp.status_code == 200
    assert test_resp.json()["delivered"] is True
    assert test_resp.json()["mode"] == "mock_local"

    # Disconnect clears chat ID & disables Telegram
    disc_resp = client.post("/api/v1/notifications/telegram/disconnect", headers=user_a_headers)
    assert disc_resp.status_code == 200
    assert disc_resp.json()["telegram_connected"] is False
    assert disc_resp.json()["telegram_enabled"] is False
    assert disc_resp.json()["telegram_chat_id_masked"] is None

    # Test notification fails after disconnect
    post_disc_test = client.post("/api/v1/notifications/test", headers=user_a_headers)
    assert post_disc_test.status_code == 400
    assert post_disc_test.json()["error"]["code"] == "TELEGRAM_NOT_CONNECTED"


def test_telegram_webhook_deep_link_verification(client, test_settings, user_a_headers):
    test_settings.telegram_webhook_secret = "tg-webhook-secret-123"
    conn = client.post("/api/v1/notifications/telegram/connect", headers=user_a_headers)
    assert conn.status_code == 200
    code = conn.json()["verification_code"]

    # Reject missing or wrong webhook secret
    bad_hook = client.post(
        "/api/v1/notifications/telegram/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "wrong-secret"},
        json={"message": {"text": f"/start {code}", "chat": {"id": 555666777}}},
    )
    assert bad_hook.status_code == 401
    assert bad_hook.json()["error"]["code"] == "UNAUTHORIZED_WEBHOOK"

    # Valid secret + /start <code> binds chat_id automatically
    ok_hook = client.post(
        "/api/v1/notifications/telegram/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "tg-webhook-secret-123"},
        json={"message": {"text": f"/start {code}", "chat": {"id": 555666777}}},
    )
    assert ok_hook.status_code == 200
    assert ok_hook.json()["verified"] is True

    settings_resp = client.get("/api/v1/notifications/settings", headers=user_a_headers)
    assert settings_resp.status_code == 200
    assert settings_resp.json()["telegram_connected"] is True
    assert settings_resp.json()["telegram_enabled"] is True
    assert settings_resp.json()["telegram_chat_id_masked"] == "***6777"


def test_internal_worker_hmac_auth_and_endpoints(
    client, test_settings, user_a_headers
):
    # Create a post for process-post test
    post_id = client.post(
        "/api/v1/posts/ingest-manual",
        headers=user_a_headers,
        json={
            "platform": "linkedin",
            "post_url": "https://www.linkedin.com/posts/worker-test-123456",
            "content_text": "Automating scheduled cloud workers with signed HMAC verification.",
            "auto_generate_drafts": False,
        },
    ).json()["id"]
    user_id = client.get("/api/v1/profile", headers=user_a_headers).json()["id"]

    endpoints_and_bodies = [
        ("/api/v1/internal/jobs/monitor", b"{}"),
        (
            "/api/v1/internal/jobs/process-post",
            json.dumps({"post_id": post_id, "user_id": user_id, "variants": 1, "notify_telegram": False}).encode(),
        ),
        ("/api/v1/internal/jobs/daily-digest", b"{}"),
    ]

    for url, body in endpoints_and_bodies:
        # 1. Missing auth -> 401
        r_missing = client.post(url, content=body, headers={"Content-Type": "application/json"})
        assert r_missing.status_code == 401
        assert r_missing.json()["error"]["code"] == "UNAUTHORIZED_INTERNAL_JOB"

        # 2. Invalid HMAC signature -> 401
        now_ts = str(int(time.time()))
        r_bad_sig = client.post(
            url,
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Internal-Job-Timestamp": now_ts,
                "X-Internal-Job-Signature": "deadbeef" * 8,
            },
        )
        assert r_bad_sig.status_code == 401
        assert r_bad_sig.json()["error"]["code"] == "INVALID_SIGNATURE"

        # 3. Expired timestamp (>300s old) -> 401
        expired_ts = str(int(time.time()) - 600)
        expired_sig = compute_internal_signature(test_settings.internal_job_secret, expired_ts, body)
        r_expired = client.post(
            url,
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Internal-Job-Timestamp": expired_ts,
                "X-Internal-Job-Signature": expired_sig,
            },
        )
        assert r_expired.status_code == 401
        assert r_expired.json()["error"]["code"] == "SIGNATURE_EXPIRED"

        # 4. Valid HMAC-SHA256 signature -> 200
        valid_sig = compute_internal_signature(test_settings.internal_job_secret, now_ts, body)
        r_ok = client.post(
            url,
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Internal-Job-Timestamp": now_ts,
                "X-Internal-Job-Signature": valid_sig,
            },
        )
        assert r_ok.status_code == 200
        assert r_ok.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_monitoring_job_runner_official_unsupported_and_authorized_feed_idempotency(
    db_session, test_settings, user_a_id
):
    db_session.add(Profile(id=user_a_id, display_name="Monitor User"))
    db_session.flush()

    # Active target marked official_api (simulating stale active status without credentials)
    official_target = TrackedTarget(
        user_id=user_a_id,
        platform="linkedin",
        profile_url="https://www.linkedin.com/in/official-no-creds",
        display_name="Official No Creds",
        source_type="official_api",
        status="active",
    )
    # Active authorized_feed target using mock feed
    feed_target = TrackedTarget(
        user_id=user_a_id,
        platform="linkedin",
        profile_url="https://www.linkedin.com/in/mock-feed-creator",
        display_name="Mock Feed Creator",
        source_type="authorized_feed",
        status="active",
        preferences={"use_mock_feed": True},
    )
    db_session.add_all([official_target, feed_target])
    db_session.commit()

    # First monitoring cycle
    summary_1 = await run_monitoring_cycle(db_session, test_settings)
    assert summary_1["unsupported"] == 1
    assert summary_1["checked"] == 1
    assert summary_1["new_posts"] == 1
    assert summary_1["drafts_created"] >= 1

    db_session.refresh(official_target)
    db_session.refresh(feed_target)
    assert official_target.status == "unsupported"
    assert official_target.last_error_code == "SOURCE_UNAVAILABLE"
    assert feed_target.status == "active"
    assert feed_target.last_success_at is not None

    jobs = list(db_session.scalars(select(MonitoringJob)))
    assert len(jobs) == 2

    posts_after_1 = db_session.scalar(select(func.count(Post.id)))
    drafts_after_1 = db_session.scalar(select(func.count(CommentDraft.id)))
    assert posts_after_1 == 1
    assert drafts_after_1 >= 1

    # Second monitoring cycle must be idempotent (no duplicate posts or drafts)
    summary_2 = await run_monitoring_cycle(db_session, test_settings)
    assert summary_2["unsupported"] == 0  # already marked unsupported
    assert summary_2["checked"] == 1
    assert summary_2["new_posts"] == 0
    assert summary_2["drafts_created"] == 0

    assert db_session.scalar(select(func.count(Post.id))) == posts_after_1
    assert db_session.scalar(select(func.count(CommentDraft.id))) == drafts_after_1

    unsupported_logs = list(
        db_session.scalars(
            select(ActivityLog).where(ActivityLog.event_type == "source_unsupported")
        )
    )
    assert len(unsupported_logs) == 1


def test_sql_migrations_rls_and_no_hardcoded_secrets():
    repo_root = Path(__file__).resolve().parents[3]
    migrations_dir = repo_root / "infra" / "migrations"

    sql_001 = (migrations_dir / "001_initial_schema.sql").read_text(encoding="utf-8")
    sql_002 = (migrations_dir / "002_rls_policies.sql").read_text(encoding="utf-8")
    sql_003 = (migrations_dir / "003_indexes_and_triggers.sql").read_text(encoding="utf-8")

    assert sql_001.strip()
    assert sql_002.strip()
    assert sql_003.strip()

    # Every table created in 001_initial_schema.sql must have RLS enabled in 002_rls_policies.sql
    tables = re.findall(r"create table if not exists public\.([a-z_]+)", sql_001, re.IGNORECASE)
    assert len(tables) == 11
    assert "user_posts" in tables
    for table_name in tables:
        assert re.search(
            rf"alter table public\.{re.escape(table_name)}\s+enable row level security\s*;",
            sql_002,
            re.IGNORECASE,
        ), f"RLS not enabled on public.{table_name}"
        assert re.search(
            rf"on public\.{re.escape(table_name)}\b",
            sql_002,
            re.IGNORECASE,
        ), f"No RLS policy found for public.{table_name}"

    # Verify triggers & indexes exist in 003
    assert "create index if not exists" in sql_003.lower()
    assert "on_auth_user_created" in sql_003

    # Verify no hardcoded real secrets in .env.example or SQL migrations
    env_example = (repo_root / ".env.example").read_text(encoding="utf-8")
    secret_patterns = [
        r"AIza[0-9A-Za-z\-_]{35}",       # Google/Gemini API key
        r"sk-[A-Za-z0-9]{20,}",          # OpenAI-style key
        r"ghp_[A-Za-z0-9]{20,}",         # GitHub PAT
        r"\b\d{8,10}:[A-Za-z0-9_-]{35}\b",  # Telegram bot token
        r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",  # Real JWT
    ]
    for label, content in [
        (".env.example", env_example),
        ("001_initial_schema.sql", sql_001),
        ("002_rls_policies.sql", sql_002),
        ("003_indexes_and_triggers.sql", sql_003),
    ]:
        for pat in secret_patterns:
            assert not re.search(pat, content), f"Potential hardcoded secret matched {pat} in {label}"
