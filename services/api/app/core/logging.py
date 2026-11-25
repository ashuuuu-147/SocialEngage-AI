"""Structured logging configuration that redacts secrets and sensitive tokens."""

import logging
import re

SECRET_PATTERNS = [
    re.compile(r"(Bearer\s+)[A-Za-z0-9\-_\.]+", re.IGNORECASE),
    re.compile(r"(bot\d+:)[A-Za-z0-9_\-]+", re.IGNORECASE),
    re.compile(r"(api[_-]?key[\"']?\s*[:=]\s*[\"']?)[^\"'\s]+", re.IGNORECASE),
]


class SecretRedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        for pattern in SECRET_PATTERNS:
            msg = pattern.sub(r"\1[REDACTED]", msg)
        record.msg = msg
        record.args = ()
        return True


def configure_logging(level: str = "INFO") -> logging.Logger:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    logger = logging.getLogger("socialengage")
    logger.addFilter(SecretRedactingFilter())
    return logger
