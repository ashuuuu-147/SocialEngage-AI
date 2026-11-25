"""API contract, auth, ownership isolation, post deduplication, draft workflow, and account tests."""

import time
import uuid

import jwt
from sqlalchemy import func, select

from app.core.config import Settings, get_settings
from app.main import app
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
    UserPreferences,
)


def _assert_error_envelope(response, expected_status: int, expected_code: str | None = None):
    assert response.status_code == expected_status
    body = response.json()
    assert "error" in body
    err = body["error"]
    assert set(err.keys()) == {"code", "message", "request_id"}
    assert isinstance(err["code"], str) and err["code"]
    assert isinstance(err["message"], str) and err["message"]
    assert isinstance(err["request_id"], str) and err["request_id"]
    if expected_code is not None:
        assert err["code"] == expected_code
    return err


def test_health_check_and_request_id(client):
    resp = client.get("/health", headers={"X-Request-Id": "req-health-123"})
    assert resp.status_code == 200
    assert resp.headers["X-Request-Id"] == "req-health-123"
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "socialengage-api"
    assert "ai_provider" in data


def test_auth_rejection_when_dev_bypass_disabled_and_jwt_handling(client, test_settings: Settings, user_a_id):
    strict_settings = test_settings.model_copy(update={"dev_auth_bypass": False})
    app.dependency_overrides[get_settings] = lambda: strict_settings

    # Unauthenticated request without Authorization header must fail with 401 envelope
    resp = client.get("/api/v1/targets")
    _assert_error_envelope(resp, 401, "UNAUTHENTICATED")

    # Even with X-Dev-User-Id header, dev bypass must be disabled
    resp_dev_hdr = client.get("/api/v1/targets", headers={"X-Dev-User-Id": str(user_a_id)})
    _assert_error_envelope(resp_dev_hdr, 401, "UNAUTHENTICATED")

    # Malformed JWT
    resp_bad_jwt = client.get("/api/v1/targets", headers={"Authorization": "Bearer not.a.jwt"})
    _assert_error_envelope(resp_bad_jwt, 401, "INVALID_TOKEN")

    # Expired JWT
    expired_token = jwt.encode(
        {"sub": str(user_a_id), "email": "a@example.com", "exp": int(time.time()) - 60},
        strict_settings.supabase_jwt_secret,
        algorithm="HS256",
    )
    resp_expired = client.get("/api/v1/targets", headers={"Authorization": f"Bearer {expired_token}"})
    _assert_error_envelope(resp_expired, 401, "TOKEN_EXPIRED")

    # Valid HS256 JWT succeeds
    valid_token = jwt.encode(
        {
            "sub": str(user_a_id),
            "email": "usera@example.com",
            "user_metadata": {"display_name": "User A"},
            "exp": int(time.time()) + 300,
        },
        strict_settings.supabase_jwt_secret,
        algorithm="HS256",
    )
    resp_ok = client.get("/api/v1/targets", headers={"Authorization": f"Bearer {valid_token}"})
    assert resp_ok.status_code == 200
    assert resp_ok.json() == []


def test_target_crud_duplicate_invalid_url_and_honest_capabilities(client, user_a_headers):
    # Capabilities check
    cap_resp = client.get("/api/v1/sources/capabilities", headers=user_a_headers)
    assert cap_resp.status_code == 200
    caps = cap_resp.json()["capabilities"]
    official_caps = [c for c in caps if c["source_type"] == "official_api"]
    assert len(official_caps) == 2
    assert all(c["supported"] is False and c["requires_manual_fallback"] is True for c in official_caps)

    # Invalid platform URL -> 400
    bad_url = client.post(
        "/api/v1/targets",
        headers=user_a_headers,
        json={
            "platform": "linkedin",
            "profile_url": "https://example.com/in/someone",
            "source_type": "manual",
        },
    )
    _assert_error_envelope(bad_url, 400, "PLATFORM_URL_MISMATCH")

    # Create manual target -> 201 active
    created = client.post(
        "/api/v1/targets",
        headers=user_a_headers,
        json={
            "platform": "linkedin",
            "profile_url": "https://m.linkedin.com/in/alice-dev/?utm_source=share",
            "display_name": "Alice Dev",
            "source_type": "manual",
        },
    )
    assert created.status_code == 201
    t_data = created.json()
    assert t_data["status"] == "active"
    assert t_data["profile_url"] == "https://www.linkedin.com/in/alice-dev"
    assert t_data["capability"]["supported"] is True
    target_id = t_data["id"]

    # Duplicate target (even with tracking params) -> 409
    dup = client.post(
        "/api/v1/targets",
        headers=user_a_headers,
        json={
            "platform": "linkedin",
            "profile_url": "https://www.linkedin.com/in/alice-dev/",
            "source_type": "manual",
        },
    )
    _assert_error_envelope(dup, 409, "TARGET_ALREADY_EXISTS")

    # Official API target without credentials -> honest unsupported status
    official = client.post(
        "/api/v1/targets",
        headers=user_a_headers,
        json={
            "platform": "instagram",
            "profile_url": "https://www.instagram.com/creator_account/",
            "source_type": "official_api",
        },
    )
    assert official.status_code == 201
    off_data = official.json()
    assert off_data["status"] == "unsupported"
    assert off_data["last_error_code"] == "SOURCE_UNAVAILABLE"
    assert off_data["capability"]["supported"] is False
    assert off_data["capability"]["requires_manual_fallback"] is True

    # Attempting to activate unsupported official_api target keeps it unsupported
    patch_off = client.patch(
        f"/api/v1/targets/{off_data['id']}",
        headers=user_a_headers,
        json={"status": "active"},
    )
    assert patch_off.status_code == 200
    assert patch_off.json()["status"] == "unsupported"

    # Update & delete manual target
    patched = client.patch(
        f"/api/v1/targets/{target_id}",
        headers=user_a_headers,
        json={"display_name": "Alice Updated", "status": "paused"},
    )
    assert patched.status_code == 200
    assert patched.json()["display_name"] == "Alice Updated"
    assert patched.json()["status"] == "paused"

    deleted = client.delete(f"/api/v1/targets/{target_id}", headers=user_a_headers)
    assert deleted.status_code == 204
    missing = client.patch(
        f"/api/v1/targets/{target_id}",
        headers=user_a_headers,
        json={"status": "active"},
    )
    _assert_error_envelope(missing, 404, "TARGET_NOT_FOUND")


def test_strict_cross_user_ownership_isolation(client, user_a_headers, user_b_headers):
    # User A creates target, style sample, and post with drafts
    target_resp = client.post(
        "/api/v1/targets",
        headers=user_a_headers,
        json={
            "platform": "linkedin",
            "profile_url": "https://www.linkedin.com/in/user-a-target/",
            "display_name": "User A Target",
            "source_type": "manual",
        },
    )
    assert target_resp.status_code == 201
    target_id = target_resp.json()["id"]

    sample_resp = client.post(
        "/api/v1/style-samples",
        headers=user_a_headers,
        json={"sample_text": "Sharp breakdown on latency budgets—did caching help at p99?"},
    )
    assert sample_resp.status_code == 201
    sample_id = sample_resp.json()["id"]

    post_resp = client.post(
        "/api/v1/posts/ingest-manual",
        headers=user_a_headers,
        json={
            "platform": "linkedin",
            "target_id": target_id,
            "post_url": "https://www.linkedin.com/posts/alice_architecture-9988776655",
            "author_name": "User A Target",
            "content_text": "We reduced our PostgreSQL query p99 latency by 45% using partial indexes.",
            "auto_generate_drafts": True,
        },
    )
    assert post_resp.status_code == 201
    post_data = post_resp.json()
    post_id = post_data["id"]
    assert len(post_data["drafts"]) >= 1
    draft_id = post_data["drafts"][0]["id"]

    # User B listing endpoints must NOT leak User A's data
    assert client.get("/api/v1/targets", headers=user_b_headers).json() == []
    assert client.get("/api/v1/posts", headers=user_b_headers).json() == []
    assert client.get("/api/v1/drafts", headers=user_b_headers).json() == []
    assert client.get("/api/v1/style-samples", headers=user_b_headers).json() == []
    assert client.get("/api/v1/activity", headers=user_b_headers).json() == []

    # User B receives 403 UNAUTHORIZED when accessing User A's resources directly
    _assert_error_envelope(
        client.patch(f"/api/v1/targets/{target_id}", headers=user_b_headers, json={"status": "paused"}),
        403,
        "UNAUTHORIZED",
    )
    _assert_error_envelope(
        client.delete(f"/api/v1/targets/{target_id}", headers=user_b_headers),
        403,
        "UNAUTHORIZED",
    )
    _assert_error_envelope(
        client.post(f"/api/v1/targets/{target_id}/check", headers=user_b_headers),
        403,
        "UNAUTHORIZED",
    )
    _assert_error_envelope(
        client.get(f"/api/v1/posts/{post_id}", headers=user_b_headers),
        403,
        "UNAUTHORIZED",
    )
    _assert_error_envelope(
        client.post(f"/api/v1/posts/{post_id}/drafts", headers=user_b_headers, json={"variants": 1}),
        403,
        "UNAUTHORIZED",
    )
    _assert_error_envelope(
        client.patch(f"/api/v1/drafts/{draft_id}", headers=user_b_headers, json={"edited_text": "hacked"}),
        403,
        "UNAUTHORIZED",
    )
    _assert_error_envelope(
        client.post(f"/api/v1/drafts/{draft_id}/regenerate", headers=user_b_headers, json={}),
        403,
        "UNAUTHORIZED",
    )
    _assert_error_envelope(
        client.post(f"/api/v1/drafts/{draft_id}/mark", headers=user_b_headers, json={"action": "copied"}),
        403,
        "UNAUTHORIZED",
    )
    _assert_error_envelope(
        client.delete(f"/api/v1/drafts/{draft_id}", headers=user_b_headers),
        403,
        "UNAUTHORIZED",
    )
    _assert_error_envelope(
        client.delete(f"/api/v1/style-samples/{sample_id}", headers=user_b_headers),
        403,
        "UNAUTHORIZED",
    )

    # Nonexistent UUIDs return 404
    missing_id = uuid.uuid4()
    _assert_error_envelope(client.get(f"/api/v1/posts/{missing_id}", headers=user_b_headers), 404, "POST_NOT_FOUND")
    _assert_error_envelope(client.delete(f"/api/v1/drafts/{missing_id}", headers=user_b_headers), 404, "DRAFT_NOT_FOUND")


def test_manual_post_canonicalization_and_deduplication(client, db_session, user_a_headers):
    url_variant_1 = (
        "http://m.linkedin.com/posts/jane-doe_cloud-architecture-7788990011/"
        "?utm_source=share&utm_medium=member_ios&rcm=ACoAAA"
    )
    url_variant_2 = (
        "https://www.linkedin.com/posts/jane-doe_cloud-architecture-7788990011"
        "?trk=public_post"
    )

    resp1 = client.post(
        "/api/v1/posts/ingest-manual",
        headers=user_a_headers,
        json={
            "platform": "linkedin",
            "post_url": url_variant_1,
            "author_name": "Jane Doe",
            "content_text": "Scaling event-driven ingestion pipelines with idempotency keys.",
            "auto_generate_drafts": True,
        },
    )
    assert resp1.status_code == 201
    p1 = resp1.json()
    assert p1["canonical_url"] == "https://www.linkedin.com/posts/jane-doe_cloud-architecture-7788990011"
    assert p1["source_post_id"] == "7788990011"

    # Second submission with tracking params reuses the same Post row and existing drafts
    resp2 = client.post(
        "/api/v1/posts/ingest-manual",
        headers=user_a_headers,
        json={
            "platform": "linkedin",
            "post_url": url_variant_2,
            "author_name": "Jane Doe",
            "content_text": "Scaling event-driven ingestion pipelines with idempotency keys.",
            "auto_generate_drafts": True,
        },
    )
    assert resp2.status_code == 201
    p2 = resp2.json()
    assert p2["id"] == p1["id"]
    assert len(p2["drafts"]) == len(p1["drafts"])

    # Instagram URL strips igsh and extracts shortcode
    ig_resp = client.post(
        "/api/v1/posts/ingest-manual",
        headers=user_a_headers,
        json={
            "platform": "instagram",
            "post_url": "https://www.instagram.com/reel/Cx9YzAb123/?igsh=MzRlODBiNWFlZA==&utm_campaign=ig",
            "author_name": "Design Studio",
            "content_text": "Behind the scenes of our typography system overhaul.",
            "auto_generate_drafts": False,
        },
    )
    assert ig_resp.status_code == 201
    ig_data = ig_resp.json()
    assert ig_data["canonical_url"] == "https://www.instagram.com/reel/Cx9YzAb123"
    assert ig_data["source_post_id"] == "Cx9YzAb123"

    post_count = db_session.scalar(select(func.count(Post.id)))
    assert post_count == 2


def test_draft_lifecycle_and_no_auto_publish_endpoint(client, user_a_headers):
    # Verify no auto-publish route exists anywhere in the API
    route_paths = [getattr(r, "path", "") for r in app.routes]
    assert not any("publish" in path.lower() for path in route_paths)

    post_resp = client.post(
        "/api/v1/posts/ingest-manual",
        headers=user_a_headers,
        json={
            "platform": "linkedin",
            "post_url": "https://www.linkedin.com/posts/dev-ops-5544332211",
            "author_name": "DevOps Lead",
            "content_text": "Zero-downtime PostgreSQL migrations require careful lock timeout discipline.",
            "auto_generate_drafts": False,
        },
    )
    assert post_resp.status_code == 201
    post_id = post_resp.json()["id"]

    # Explicit generation
    gen_resp = client.post(
        f"/api/v1/posts/{post_id}/drafts",
        headers=user_a_headers,
        json={"variants": 2, "tone": "thoughtful", "length": "short"},
    )
    assert gen_resp.status_code == 201
    drafts = gen_resp.json()
    assert len(drafts) == 2
    draft_id = drafts[0]["id"]
    assert drafts[0]["status"] == "pending"

    # Edit draft
    edit_resp = client.patch(
        f"/api/v1/drafts/{draft_id}",
        headers=user_a_headers,
        json={"edited_text": "Lock timeouts saved us during a 400M-row index backfill last quarter."},
    )
    assert edit_resp.status_code == 200
    assert edit_resp.json()["status"] == "edited"
    assert "400M-row" in edit_resp.json()["edited_text"]

    # Regenerate draft
    regen_resp = client.post(
        f"/api/v1/drafts/{draft_id}/regenerate",
        headers=user_a_headers,
        json={"tone": "concise", "instruction": "Ask a short follow-up question"},
    )
    assert regen_resp.status_code == 200
    assert regen_resp.json()["status"] == "pending"
    assert regen_resp.json()["edited_text"] is None
    assert regen_resp.json()["generation_metadata"]["regenerated"] is True

    # Mark allowed actions: copied, opened, skipped, archived
    for action in ("copied", "opened", "skipped", "archived"):
        mark_resp = client.post(
            f"/api/v1/drafts/{draft_id}/mark",
            headers=user_a_headers,
            json={"action": action},
        )
        assert mark_resp.status_code == 200
        assert mark_resp.json()["status"] == action

    # Invalid action (e.g. publish) returns 400 VALIDATION_ERROR
    bad_mark = client.post(
        f"/api/v1/drafts/{draft_id}/mark",
        headers=user_a_headers,
        json={"action": "publish"},
    )
    _assert_error_envelope(bad_mark, 400, "VALIDATION_ERROR")

    # Delete draft
    del_resp = client.delete(f"/api/v1/drafts/{draft_id}", headers=user_a_headers)
    assert del_resp.status_code == 204
    remaining = client.get("/api/v1/drafts", headers=user_a_headers).json()
    assert all(d["id"] != draft_id for d in remaining)


def test_preferences_style_samples_overview_export_and_cascading_delete(
    client, db_session, user_a_id, user_a_headers
):
    # Preferences GET & PUT
    prefs_get = client.get("/api/v1/preferences", headers=user_a_headers)
    assert prefs_get.status_code == 200
    prefs_put = client.put(
        "/api/v1/preferences",
        headers=user_a_headers,
        json={
            "tone": "direct",
            "length": "medium",
            "emoji_level": "none",
            "relevance_threshold": 0.6,
            "avoid_phrases": ["synergy", "game changer"],
            "preferred_topics": ["distributed systems", "python"],
            "excluded_topics": ["crypto giveaway"],
        },
    )
    assert prefs_put.status_code == 200
    assert prefs_put.json()["tone"] == "direct"
    assert prefs_put.json()["avoid_phrases"] == ["synergy", "game changer"]

    # Style samples CRUD
    sample = client.post(
        "/api/v1/style-samples",
        headers=user_a_headers,
        json={"sample_text": "Clean trade-off analysis; curious how you measured cold-start latency."},
    )
    assert sample.status_code == 201
    sample_id = sample.json()["id"]
    assert len(client.get("/api/v1/style-samples", headers=user_a_headers).json()) == 1

    # Target + Post + Draft + Profile update
    target = client.post(
        "/api/v1/targets",
        headers=user_a_headers,
        json={
            "platform": "linkedin",
            "profile_url": "https://www.linkedin.com/in/export-test-user",
            "source_type": "manual",
        },
    ).json()
    post = client.post(
        "/api/v1/posts/ingest-manual",
        headers=user_a_headers,
        json={
            "platform": "linkedin",
            "target_id": target["id"],
            "post_url": "https://www.linkedin.com/posts/export-test-11223344",
            "content_text": "Python 3.13 async improvements cut our API tail latency noticeably.",
            "auto_generate_drafts": True,
        },
    ).json()
    client.patch(
        "/api/v1/profile",
        headers=user_a_headers,
        json={"display_name": "Export Tester", "timezone": "UTC"},
    )

    # Overview & activity
    overview = client.get("/api/v1/overview", headers=user_a_headers)
    assert overview.status_code == 200
    ov = overview.json()
    assert ov["tracked_profiles"] == 1
    assert ov["active_profiles"] == 1
    assert ov["new_posts_detected"] == 1
    assert ov["drafts_awaiting_review"] == len(post["drafts"])
    assert ov["monitoring_health"] == "healthy"
    assert len(ov["recent_activity"]) >= 1

    # Export data
    export_resp = client.get("/api/v1/account/export", headers=user_a_headers)
    assert export_resp.status_code == 200
    exported = export_resp.json()
    assert exported["profile"]["display_name"] == "Export Tester"
    assert exported["preferences"]["tone"] == "direct"
    assert len(exported["targets"]) == 1
    assert len(exported["style_samples"]) == 1
    assert len(exported["drafts"]) == len(post["drafts"])
    assert len(exported["activity_logs"]) >= 1

    # Delete style sample check before full account delete
    assert client.delete(f"/api/v1/style-samples/{sample_id}", headers=user_a_headers).status_code == 204

    # Cascading account deletion
    del_acct = client.delete("/api/v1/account", headers=user_a_headers)
    assert del_acct.status_code == 204

    db_session.expire_all()
    assert db_session.get(Profile, user_a_id) is None
    assert db_session.get(UserPreferences, user_a_id) is None
    assert db_session.get(NotificationSettings, user_a_id) is None
    assert db_session.scalar(select(func.count(TrackedTarget.id)).where(TrackedTarget.user_id == user_a_id)) == 0
    assert db_session.scalar(select(func.count(CommentDraft.id)).where(CommentDraft.user_id == user_a_id)) == 0
    assert db_session.scalar(select(func.count(StyleSample.id)).where(StyleSample.user_id == user_a_id)) == 0
    assert db_session.scalar(select(func.count(ActivityLog.id)).where(ActivityLog.user_id == user_a_id)) == 0
    assert db_session.scalar(select(func.count(TargetPost.id))) == 0
    assert db_session.scalar(select(func.count(MonitoringJob.id))) == 0


def test_shared_public_url_manual_intake_isolation(client, db_session, user_a_headers, user_b_headers):
    shared_url = "https://www.linkedin.com/posts/public-speaker_ai-systems-5566778899"
    resp_a = client.post(
        "/api/v1/posts/ingest-manual",
        headers=user_a_headers,
        json={
            "platform": "linkedin",
            "post_url": shared_url,
            "content_text": "Designing resilient event pipelines requires explicit idempotency keys.",
            "auto_generate_drafts": True,
        },
    )
    assert resp_a.status_code == 201
    post_a = resp_a.json()
    assert len(post_a["drafts"]) >= 1

    # User B ingests the exact same public URL independently (no target_id)
    resp_b = client.post(
        "/api/v1/posts/ingest-manual",
        headers=user_b_headers,
        json={
            "platform": "linkedin",
            "post_url": shared_url,
            "content_text": "Designing resilient event pipelines requires explicit idempotency keys.",
            "auto_generate_drafts": True,
        },
    )
    assert resp_b.status_code == 201
    post_b = resp_b.json()

    # Same deduplicated Post row, but User B has independent drafts and sees the post in GET /posts
    assert post_b["id"] == post_a["id"]
    assert db_session.scalar(select(func.count(Post.id))) == 1
    assert len(post_b["drafts"]) >= 1
    assert post_b["drafts"][0]["id"] != post_a["drafts"][0]["id"]

    user_b_posts = client.get("/api/v1/posts", headers=user_b_headers).json()
    assert len(user_b_posts) == 1
    assert user_b_posts[0]["id"] == post_b["id"]
    assert client.get(f"/api/v1/posts/{post_b['id']}", headers=user_b_headers).status_code == 200
