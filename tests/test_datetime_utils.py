from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import DateTime, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from app.utils.datetime import (
    as_utc,
    normalize_aware_iso_datetime,
    parse_aware_iso_datetime,
    serialize_utc_datetime,
    utc_now,
)


def test_utc_now_returns_aware_utc_datetime():
    value = utc_now()
    assert value.tzinfo is timezone.utc
    assert value.utcoffset() == timedelta(0)


def test_serialize_contract_defined_naive_utc_without_shifting_clock_fields():
    value = datetime(2026, 8, 17, 13, 15, 9, 123456)
    assert as_utc(value) == datetime(2026, 8, 17, 13, 15, 9, 123456, tzinfo=timezone.utc)
    assert serialize_utc_datetime(value) == "2026-08-17T13:15:09.123456Z"


def test_serialize_aware_utc_and_positive_offset_to_z():
    utc_value = datetime(2026, 8, 17, 13, 15, 9, tzinfo=timezone.utc)
    shanghai_value = datetime(2026, 8, 17, 21, 15, 9, tzinfo=timezone(timedelta(hours=8)))
    assert serialize_utc_datetime(utc_value) == "2026-08-17T13:15:09Z"
    assert serialize_utc_datetime(shanghai_value) == "2026-08-17T13:15:09Z"


def test_serialize_none_and_parse_supported_aware_iso_formats():
    assert serialize_utc_datetime(None) is None
    assert normalize_aware_iso_datetime(None) is None
    assert normalize_aware_iso_datetime("2026-08-17T13:15:09Z") == "2026-08-17T13:15:09Z"
    assert normalize_aware_iso_datetime("2026-08-17T13:15:09+00:00") == "2026-08-17T13:15:09Z"
    assert normalize_aware_iso_datetime("2026-08-17T21:15:09+08:00") == "2026-08-17T13:15:09Z"


def test_unknown_naive_iso_string_is_rejected_instead_of_assumed_utc():
    with pytest.raises(ValueError, match="explicit timezone"):
        parse_aware_iso_datetime("2026-08-17T13:15:09")


def test_sqlite_round_trip_can_drop_tzinfo_but_serializer_restores_utc_contract():
    class Base(DeclarativeBase):
        pass

    class TimestampRecord(Base):
        __tablename__ = "timestamp_records"
        id: Mapped[int] = mapped_column(primary_key=True)
        created_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as database:
        database.add(TimestampRecord(
            created_time=datetime(2026, 8, 17, 13, 15, 9, 654321, tzinfo=timezone.utc)
        ))
        database.commit()
        stored = database.scalar(select(TimestampRecord))
        assert stored is not None
        assert stored.created_time.tzinfo is None
        assert serialize_utc_datetime(stored.created_time) == "2026-08-17T13:15:09.654321Z"
    engine.dispose()
