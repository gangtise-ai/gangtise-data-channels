# GENERATED FILE. Do not edit. Source: core/src/gangtise_core/errors.py
# Regenerate: python3 scripts/generate.py
"""Typed failures that adapters map to MCP isError / CLI exit codes / skill text."""
from __future__ import annotations

from typing import Any, Optional

from .hints import hint_for

# Codes whose fix is on the caller's side (arguments), CLI exit 2.
PARAM_CODES = frozenset(
    {
        "100001", "100002", "100003", "100004", "100005", "100006",
        "110001", "110002", "120001", "130004", "130005", "140002",
        "240003", "900001",
    }
)


class GangtiseError(Exception):
    """Base error. `exit_code` is the CLI mapping: 1 hard fail, 2 param, 3 partial."""

    exit_code = 1

    def __init__(self, message: str, *, code: str = "", trace_id: str = "") -> None:
        super().__init__(message)
        self.message = message
        self.code = str(code or "")
        self.trace_id = str(trace_id or "")

    def __str__(self) -> str:
        parts = [self.message]
        if self.code:
            parts.append(f"code={self.code}")
        if self.trace_id:
            parts.append(f"traceId={self.trace_id}")
        return " ".join(parts)


class ValidationError(GangtiseError):
    """Argument refused locally, before any request (no billing). CLI exit 2."""

    exit_code = 2

    def __str__(self) -> str:
        return self.message


def _trace_from_body(body: Any) -> str:
    if isinstance(body, dict):
        value = body.get("traceId") or body.get("_traceId") or body.get("trace_id")
        if isinstance(value, (str, int)) and not isinstance(value, bool) and str(value):
            return str(value)
    return ""


class ApiError(GangtiseError):
    """Server envelope was not OK (or HTTP failed)."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "",
        http: int = 0,
        trace_id: str = "",
        body: Optional[Any] = None,
        retry_after_ms: Optional[int] = None,
        hint: Optional[str] = None,
    ) -> None:
        super().__init__(message, code=code, trace_id=str(trace_id or "") or _trace_from_body(body))
        self.http = int(http or 0)
        self.body = body
        self.retry_after_ms = retry_after_ms
        # Precedence: explicit override > message-specific > per-code.
        self.hint = hint if hint is not None else hint_for(self.code, message)
        if self.code in PARAM_CODES or (400 <= self.http < 500 and self.http not in {401, 403, 429}):
            self.exit_code = 2

    def __str__(self) -> str:
        head = f"API error ({self.code})" if self.code else "API error"
        if self.trace_id:
            head += f" [trace {self.trace_id}]"
        msg = self.message
        if self.http >= 400 and "HTTP" not in msg:
            msg = f"{msg} (HTTP {self.http})"
        return f"{head}: {msg}" + (f" {self.hint}" if self.hint else "")


class StructuralError(GangtiseError):
    """Response shape is unsafe to consume (fieldList mismatch, missing rows, …)."""


class PartialResultError(GangtiseError):
    """Some items succeeded; remainder failed. CLI exit 3."""

    exit_code = 3
