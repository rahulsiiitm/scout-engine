from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo


DISPLAY_TZ = ZoneInfo("Asia/Kolkata")


def to_utc_iso(value: str, source_timezone: str | None = None) -> str:
    """Parse an ISO-8601-like timestamp and normalize it to UTC.

    Naive values require an explicit source timezone. This intentionally refuses
    to guess because deadline drift is worse than missing data.
    """
    normalized = value.replace("Z", "+00:00")
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        if not source_timezone:
            raise ValueError("Naive datetime requires source_timezone")
        dt = dt.replace(tzinfo=ZoneInfo(source_timezone))
    return dt.astimezone(timezone.utc).isoformat()


def display_ist(value: str) -> str:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("UTC/offset-aware timestamp required")
    return dt.astimezone(DISPLAY_TZ).strftime("%Y-%m-%d %H:%M IST")


def days_until(value: str, now: datetime | None = None) -> float:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("UTC/offset-aware timestamp required")
    current = now or datetime.now(timezone.utc)
    return (dt.astimezone(timezone.utc) - current.astimezone(timezone.utc)).total_seconds() / 86400
