from datetime import UTC, datetime

import pytest

from app.jobs.analyze import parse_as_of

NOW = datetime(2026, 11, 26, 12, 0, tzinfo=UTC)


def test_without_as_of_uses_now():
    assert parse_as_of(None, now=NOW) == NOW


def test_as_of_reads_an_iso_instant():
    assert parse_as_of("2026-10-17T20:35:51Z", now=NOW) == datetime(
        2026, 10, 17, 20, 35, 51, tzinfo=UTC
    )


def test_as_of_without_timezone_is_rejected():
    # Una fecha sin zona se leería en la hora local de quien corre el job: otro corte.
    with pytest.raises(ValueError, match="zona horaria"):
        parse_as_of("2026-10-17T20:35:51", now=NOW)


def test_as_of_in_the_future_is_rejected():
    with pytest.raises(ValueError, match="futuro"):
        parse_as_of("2026-12-01T00:00:00Z", now=NOW)
