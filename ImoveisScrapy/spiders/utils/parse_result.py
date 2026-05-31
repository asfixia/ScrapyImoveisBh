"""Structured parse warnings (optional) and logging helpers."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

LOG = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ParseWarning:
    """One non-fatal parse issue with enough context to debug."""

    code: str
    message: str
    listing_id: str | None = None
    url: str | None = None
    exc_type: str | None = None


def log_parse_warning(
    code: str,
    message: str,
    *,
    listing_id: str | None = None,
    url: str | None = None,
    exc: BaseException | None = None,
    warnings_out: list[ParseWarning] | None = None,
) -> None:
    extra: dict[str, Any] = {"code": code}
    if listing_id:
        extra["listing_id"] = listing_id
    if url:
        extra["url"] = url
    LOG.warning("%s: %s", code, message, extra=extra)
    if warnings_out is not None:
        warnings_out.append(
            ParseWarning(
                code=code,
                message=message,
                listing_id=listing_id,
                url=url,
                exc_type=type(exc).__name__ if exc else None,
            )
        )
