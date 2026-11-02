"""Date / datetime arguments, ported from gangtise-openapi-cli `src/core/args.ts`.

Year-FIRST only: `2026/07/01` means one day to every reader, while `01-07-2026` is
7 January to the server (it reads year-last month-first) and 1 July to a European.
Forwarding year-last would hand half of the callers data six months off with HTTP 200,
so it is refused locally — no request, no billing.

Wall-clock inputs converted to epoch millis are anchored to Beijing time (UTC+8), not
to the machine's zone, so "2026-08-01" is the same instant on a UTC host and a CST laptop.
"""
from __future__ import annotations

import datetime
import re
from typing import Optional

from .errors import ValidationError

CST = datetime.timezone(datetime.timedelta(hours=8))

# Backreference keeps the separator consistent, so `2026-07/01` is not a date.
_YEAR_FIRST_DATE = re.compile(r"^(\d{4})([-/]?)(\d{2})\2(\d{2})$")
# Groups: 1=year 2=separator 3=month 4=day 5=hour 6=minute 7=second.
_LOCAL_DATETIME = re.compile(r"^(\d{4})([-/]?)(\d{2})\2(\d{2})(?:[ T](\d{2}):(\d{2})(?::(\d{2}))?)?$")

_YEAR_LAST_NOTE = (
    "year-last layouts are refused because the API reads them month-first (US convention): "
    '"01-07-2026" means 7 January, not 1 July'
)
_DATE_EXPECTED = "expected YYYY-MM-DD (YYYY/MM/DD and YYYYMMDD also accepted)"
_DATETIME_EXPECTED = (
    'expected a Unix timestamp or "YYYY-MM-DD" optionally with " HH:mm[:ss]" '
    "(space or T separator; YYYY/MM/DD and YYYYMMDD also accepted)"
)


def _fields_valid(year: int, month: int, day: int, hh: int = 0, mi: int = 0, ss: int = 0) -> bool:
    if not 1 <= month <= 12:
        return False
    leap = (year % 4 == 0 and year % 100 != 0) or year % 400 == 0
    dim = [31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1]
    return 1 <= day <= dim and hh <= 23 and mi <= 59 and ss <= 59


def normalize_date(value: str) -> Optional[str]:
    """`YYYY-MM-DD` | `YYYY/MM/DD` | `YYYYMMDD` → `YYYY-MM-DD`; anything else None."""
    m = _YEAR_FIRST_DATE.match((value or "").strip())
    return f"{m.group(1)}-{m.group(3)}-{m.group(4)}" if m else None


def parse_date_option(value: str, option: str = "date") -> str:
    """Validate a calendar date and return it as `YYYY-MM-DD`."""
    normalized = normalize_date(value)
    if normalized is None:
        raise ValidationError(f'Invalid {option}: {_DATE_EXPECTED}, got "{value}" — {_YEAR_LAST_NOTE}')
    y, mo, d = (int(x) for x in normalized.split("-"))
    if not _fields_valid(y, mo, d):
        raise ValidationError(f'Invalid {option}: "{value}" is not a real calendar date')
    return normalized


def _epoch_millis(value: str) -> Optional[int]:
    """Exactly 10 (seconds) or 13 (millis) digits; judged by digit count, not magnitude."""
    if re.fullmatch(r"\d{13}", value):
        return int(value)
    if re.fullmatch(r"\d{10}", value):
        return int(value) * 1000
    return None


def _datetime_parts(value: str):
    m = _LOCAL_DATETIME.match(value)
    if not m:
        return None
    y, _sep, mo, d, hh, mi, ss = m.groups()
    parts = (int(y), int(mo), int(d), int(hh or 0), int(mi or 0), int(ss or 0))
    return parts if _fields_valid(*parts) else None


def parse_datetime_option(value: str, option: str = "time") -> str:
    """Pass-through datetime guard: epoch unchanged; date part rewritten to `YYYY-MM-DD`."""
    s = (value or "").strip()
    if _epoch_millis(s) is not None:
        return s
    if _datetime_parts(s) is None:
        raise ValidationError(f'Invalid {option}: {_DATETIME_EXPECTED}, got "{value}" — {_YEAR_LAST_NOTE}')
    m = _LOCAL_DATETIME.match(s)
    assert m is not None
    date_len = 8 if m.group(2) == "" else 10
    return f"{m.group(1)}-{m.group(3)}-{m.group(4)}{s[date_len:]}"


def to_timestamp13(day: str, *, end_of_day: bool = False, option: str = "date") -> int:
    """Epoch / date / datetime → 13-digit millis in Beijing time.

    `end_of_day` applies to a bare date only: it yields the next day's 00:00 so a
    `[start, end)` window includes the whole end date.
    """
    s = str(day if day is not None else "").strip()
    ts = _epoch_millis(s)
    if ts is not None:
        return ts
    parts = _datetime_parts(s)
    if parts is None:
        raise ValidationError(f'Invalid {option}: {_DATETIME_EXPECTED}, got "{day}" — {_YEAR_LAST_NOTE}')
    dt = datetime.datetime(*parts, tzinfo=CST)
    if end_of_day and normalize_date(s) is not None:
        dt += datetime.timedelta(days=1)
    return int(dt.timestamp() * 1000)


def maybe_timestamp13(day: Optional[str], *, end_of_day: bool = False, option: str = "date") -> Optional[int]:
    if day is None or str(day).strip() == "":
        return None
    return to_timestamp13(day, end_of_day=end_of_day, option=option)


def beijing_today() -> str:
    """Beijing calendar date for "default: today" options, whatever the machine zone."""
    return datetime.datetime.now(CST).strftime("%Y-%m-%d")
