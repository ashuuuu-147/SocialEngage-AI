"""Shared pytest fixtures using isolated temporary SQLite databases."""

import uuid
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.core.security import rate_limiter
from app.db.session import Base, get_db
from app.main import app
from app.models import entities  # noqa: F401


@pytest.fixture()
def test_settings(tmp_path: Path) -> Settings:
    db_file = tmp_path / "test_socialengage.db"
    return Settings(
        app_env="test",
        database_url=f"sqlite:///{db_file.as_posix()}",
        dev_auth_bypass=True,
        enable_mock_sources=True,
        ai_provider="mock",
        supabase_jwt_secret="test-supabase-jwt-secret-key-at-least-32-bytes",
        internal_job_secret="test-internal-job-secret-for-hmac-verification",
        linkedin_access_token="",
        instagram_access_token="",
        telegram_bot_token="",
        telegram_bot_username="SocialEngageTestBot",
        ai_daily_user_quota=50,
    )


@pytest.fixture()
def db_session_factory(test_settings: Settings):
    engine = create_engine(
        test_settings.database_url,
        connect_args={"check_same_thread": False},
        future=True,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    try:
        yield TestingSessionLocal
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def db_session(db_session_factory) -> Generator[Session, None, None]:
    session = db_session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session_factory, test_settings: Settings) -> Generator[TestClient, None, None]:
    rate_limiter._hits.clear()

    def _override_get_db() -> Generator[Session, None, None]:
        db = db_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_settings] = lambda: test_settings

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    rate_limiter._hits.clear()


@pytest.fixture()
def user_a_id() -> uuid.UUID:
    return uuid.UUID("11111111-1111-1111-1111-111111111111")


@pytest.fixture()
def user_b_id() -> uuid.UUID:
    return uuid.UUID("22222222-2222-2222-2222-222222222222")


@pytest.fixture()
def user_a_headers(user_a_id: uuid.UUID) -> dict[str, str]:
    return {"X-Dev-User-Id": str(user_a_id)}


@pytest.fixture()
def user_b_headers(user_b_id: uuid.UUID) -> dict[str, str]:
    return {"X-Dev-User-Id": str(user_b_id)}
