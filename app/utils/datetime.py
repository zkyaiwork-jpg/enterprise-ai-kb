"""UTC datetime helpers for application persistence and API responses."""

from datetime import datetime, timezone
from typing import overload


def utc_now() -> datetime:
    """Return the current time as an aware UTC datetime."""
    return datetime.now(timezone.utc)


def as_utc(value: datetime) -> datetime:
    """Return ``value`` in UTC without shifting contract-defined naive values.

    SQLite drops timezone information from SQLAlchemy ``DateTime`` values. The
    application's ORM datetime columns are contractually stored as UTC, so a
    naive value from those columns only needs its UTC timezone restored.
    """
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


@overload
def serialize_utc_datetime(value: datetime) -> str: ...


@overload
def serialize_utc_datetime(value: None) -> None: ...


def serialize_utc_datetime(value: datetime | None) -> str | None:
    """Serialize a datetime as an explicit ISO 8601 UTC string using ``Z``."""
    if value is None:
        return None
    return as_utc(value).isoformat().replace("+00:00", "Z")


def parse_aware_iso_datetime(value: str) -> datetime:
    """Parse an ISO 8601 string that already carries explicit timezone data.

    Naive strings are rejected because their source timezone is unknown. ORM
    datetime values should use :func:`as_utc` instead, where the UTC contract is
    explicit.
    """
    normalized = value.strip()
    if normalized.endswith(("Z", "z")):
        normalized = f"{normalized[:-1]}+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("ISO datetime must include an explicit timezone offset")
    return parsed


def normalize_aware_iso_datetime(value: str | None) -> str | None:
    """Normalize an offset-aware ISO 8601 string to the UTC API contract."""
    if value is None:
        return None
    return serialize_utc_datetime(parse_aware_iso_datetime(value))
