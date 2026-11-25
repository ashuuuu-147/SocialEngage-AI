"""Preflight validator before starting SocialEngage AI in production."""

import os
import sys

REQUIRED_PROD_VARS = [
    "DATABASE_URL",
    "SUPABASE_URL",
    "INTERNAL_JOB_SECRET",
    "CORS_ORIGINS",
    "WEB_APP_URL",
]


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    app_env = os.getenv("APP_ENV", "development")
    if app_env != "production":
        warnings.append(f"APP_ENV is '{app_env}' (expected 'production' for cloud deployment).")

    if os.getenv("DEV_AUTH_BYPASS", "false").lower() == "true":
        errors.append("DEV_AUTH_BYPASS must be 'false' in production.")

    if os.getenv("ENABLE_MOCK_SOURCES", "false").lower() == "true":
        warnings.append("ENABLE_MOCK_SOURCES is 'true'; set to 'false' in production.")

    db_url = os.getenv("DATABASE_URL", "")
    if not db_url or db_url.startswith("sqlite"):
        errors.append("DATABASE_URL must point to PostgreSQL/Supabase in production (not sqlite).")

    for var in REQUIRED_PROD_VARS:
        val = os.getenv(var, "").strip()
        if not val or "your-" in val or "replace-with" in val:
            errors.append(f"Missing or placeholder environment variable: {var}")

    ai_provider = os.getenv("AI_PROVIDER", "mock")
    if ai_provider == "gemini" and not os.getenv("GEMINI_API_KEY"):
        errors.append("AI_PROVIDER=gemini requires GEMINI_API_KEY.")
    elif ai_provider == "openai_compatible" and (not os.getenv("AI_BASE_URL") or not os.getenv("AI_API_KEY")):
        errors.append("AI_PROVIDER=openai_compatible requires AI_BASE_URL and AI_API_KEY.")
    elif ai_provider == "mock":
        warnings.append("AI_PROVIDER=mock is active; set AI_PROVIDER=gemini with GEMINI_API_KEY for real drafts.")

    if not os.getenv("TELEGRAM_BOT_TOKEN"):
        warnings.append("TELEGRAM_BOT_TOKEN is unset; Telegram notifications will be disabled.")

    if warnings:
        print("WARNINGS:")
        for w in warnings:
            print(f"  - {w}")

    if errors:
        print("FAILED PREFLIGHT CHECKS:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("Production environment preflight checks PASSED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
