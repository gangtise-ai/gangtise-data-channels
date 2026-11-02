from datetime import datetime, timedelta, timezone

from gangtise_core.errors import ValidationError
from gangtise_core.timeutil import (
    maybe_timestamp13,
    parse_date_option,
    parse_datetime_option,
    to_timestamp13,
)
import pytest

CST = timezone(timedelta(hours=8))


def test_timestamp_is_cst_not_naive():
    expected = int(datetime(2026, 9, 1, tzinfo=CST).timestamp() * 1000)
    assert to_timestamp13("2026-09-01") == expected


def test_rejects_us_style_dates():
    with pytest.raises(ValidationError) as ei:
        to_timestamp13("01-07-2026")
    assert ei.value.exit_code == 2


# Ported from gangtise-openapi-cli tests/unit/args.test.ts (parseDateOption).

def test_accepts_canonical_date():
    assert parse_date_option("2026-07-01", "--start-date") == "2026-07-01"


@pytest.mark.parametrize("value", ["2026/07/01", "20260701"])
def test_accepts_other_year_first_layouts_and_normalizes(value):
    assert parse_date_option(value, "--start-date") == "2026-07-01"


@pytest.mark.parametrize("value", ["2026-07/01", "2026/07-01"])
def test_rejects_mixed_separator(value):
    with pytest.raises(ValidationError):
        parse_date_option(value, "--start-date")


@pytest.mark.parametrize("value", ["07/01/2026", "01-07-2026", "2026-7-1", "July 1", "", "2026-07-01T00:00"])
def test_rejects_year_last_and_other_shapes(value):
    with pytest.raises(ValidationError) as ei:
        parse_date_option(value, "--start-date")
    assert "--start-date" in str(ei.value)


@pytest.mark.parametrize("value", ["2026-02-30", "2026-13-01", "2026-00-10", "2026-04-31"])
def test_rejects_non_existent_calendar_dates(value):
    with pytest.raises(ValidationError, match="not a real calendar date"):
        parse_date_option(value, "--end-date")


def test_century_leap_rule():
    assert parse_date_option("2000-02-29", "d") == "2000-02-29"
    with pytest.raises(ValidationError):
        parse_date_option("1900-02-29", "d")


def test_early_year_is_not_mistaken_for_non_existent():
    assert parse_date_option("0050-01-01", "d") == "0050-01-01"


# parseDatetimeOption

def test_datetime_keeps_canonical_and_epoch():
    assert parse_datetime_option("2026-07-01 09:30:00", "--start-time") == "2026-07-01 09:30:00"
    assert parse_datetime_option("2026-07-01T09:30", "--start-time") == "2026-07-01T09:30"
    assert parse_datetime_option("1751333400", "--start-time") == "1751333400"
    assert parse_datetime_option("1751333400000", "--start-time") == "1751333400000"


def test_datetime_normalizes_only_the_date_part():
    assert parse_datetime_option("2026/07/01 09:30", "t") == "2026-07-01 09:30"
    assert parse_datetime_option("20260701 09:30:05", "t") == "2026-07-01 09:30:05"


@pytest.mark.parametrize("value", ["07/01/2026 09:30", "01-07-2026", "2026-07-01 24:00", "2026-07-01 09:60", "12345678901"])
def test_datetime_rejects_year_last_and_bad_clock(value):
    with pytest.raises(ValidationError):
        parse_datetime_option(value, "--start-time")


# toTimestamp13 (Beijing-anchored)

def test_timestamp_passes_through_13_digits_and_scales_10_digits():
    assert to_timestamp13("1751333400000") == 1751333400000
    assert to_timestamp13("1751333400") == 1751333400000


def test_timestamp_datetime_is_beijing_wall_clock():
    expected = int(datetime(2026, 8, 1, 9, 30, tzinfo=CST).timestamp() * 1000)
    assert to_timestamp13("2026-08-01 09:30") == expected
    assert to_timestamp13("2026/08/01T09:30:00") == expected


def test_end_of_day_only_extends_bare_dates():
    day = int(datetime(2026, 8, 2, tzinfo=CST).timestamp() * 1000)
    assert to_timestamp13("2026-08-01", end_of_day=True) == day
    at = int(datetime(2026, 8, 1, 18, 0, tzinfo=CST).timestamp() * 1000)
    assert to_timestamp13("2026-08-01 18:00", end_of_day=True) == at


def test_maybe_timestamp_skips_empty():
    assert maybe_timestamp13(None) is None
    assert maybe_timestamp13("") is None
