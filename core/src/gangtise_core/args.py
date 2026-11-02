"""Numeric argument validation, ported from gangtise-openapi-cli `src/core/args.ts`.

Plain decimal only: Python's `int()` / `float()` also take `1e3`, `inf`, `１２`
(full-width digits) or `1_000`, spellings nobody means as a row count.
"""
from __future__ import annotations

import math
import re
from typing import Optional, Union

from .errors import ValidationError

_INT = re.compile(r"^-?[0-9]+$")
_DEC = re.compile(r"^-?[0-9]+(\.[0-9]+)?$")
_MAX_SAFE_INT = 2**53 - 1

Number = Union[int, float]


def parse_number_option(
    value: Union[str, int, float, None],
    option: str,
    *,
    integer: bool = False,
    min: Optional[Number] = None,
    max: Optional[Number] = None,
) -> Number:
    if value is None or str(value).strip() == "":
        raise ValidationError(f"Invalid {option}: expected a number")
    if isinstance(value, bool):
        raise ValidationError(f"Invalid {option}: expected a number")
    if isinstance(value, str):
        text = value.strip()
        if not (_INT if integer else _DEC).match(text):
            kind = "an integer" if integer else "a number"
            raise ValidationError(f"Invalid {option}: expected {kind} written in plain decimal, got '{value}'")
        parsed: Number = int(text) if _INT.match(text) else float(text)
    else:
        parsed = value
    if isinstance(parsed, float) and not math.isfinite(parsed):
        raise ValidationError(f"Invalid {option}: expected a finite number")
    if integer:
        if isinstance(parsed, float):
            if not parsed.is_integer():
                raise ValidationError(f"Invalid {option}: expected an integer")
            parsed = int(parsed)
        if abs(parsed) > _MAX_SAFE_INT:
            raise ValidationError(f"Invalid {option}: expected an integer")
    if min is not None and parsed < min:
        raise ValidationError(f"Invalid {option}: expected a number >= {min}")
    if max is not None and parsed > max:
        raise ValidationError(f"Invalid {option}: expected a number <= {max}")
    return parsed


def parse_from(value: Union[str, int, None], option: str = "--page-from") -> int:
    return int(parse_number_option("0" if value is None else value, option, integer=True, min=0))


def parse_size(value: Union[str, int, None], option: str = "--limit") -> Optional[int]:
    if value is None:
        return None
    return int(parse_number_option(value, option, integer=True, min=1))
