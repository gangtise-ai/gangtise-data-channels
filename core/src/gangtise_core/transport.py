"""HTTP transport: unwrap envelope, retry policy, no-replay for billed endpoints.

Retry semantics follow gangtise-openapi-cli `src/core/transport.ts`:

- "retry" (default): 429 / 500 / 502 / 503 / 504, the generic 999999 code, and any
  network or timeout error.
- "no-replay": never resend a request the server may already have executed (a replay
  can double-bill). Only 429 (rejected before processing) and connect-phase / DNS
  failures (the request never left the machine) retry.
- "no-999999" (EDE indicator endpoints): like "retry" except 999999, which is a
  server-side fault there and replaying an already-billed query buys nothing.

999011 (bad AK/SK) and 140002 (terminal processing failure) are never retried.
"""
from __future__ import annotations

import email.utils
import os
import random
import sys
import time
from typing import Any, Literal, Mapping, Optional

import requests

from .auth import authorized_request
from .endpoints import match_endpoint, retry_policy_for_url
from .envelope import unwrap
from .errors import ApiError, PartialResultError
from .hints import hint_for
from .tables import fail_list_of

RetryPolicy = Literal["retry", "no-replay", "no-999999"]

TERMINAL_API_CODES = frozenset({"999011", "140002"})
RETRYABLE_API_CODES = frozenset({"999999"})
RETRYABLE_HTTP_STATUS = frozenset({429, 500, 502, 503, 504})
RETRY_AFTER_CEILING_MS = 60_000
DEFAULT_RETRIES = 2
BASE_DELAY_MS = 400
MAX_DELAY_MS = 4_000

_CONNECT_PHASE_MARKERS = (
    "NewConnectionError",
    "NameResolutionError",
    "Failed to resolve",
    "Name or service not known",
    "nodename nor servname",
    "Temporary failure in name resolution",
    "Connection refused",
)


def _is_connect_phase(err: BaseException) -> bool:
    """True when the request provably never reached the server."""
    if isinstance(err, requests.exceptions.ConnectTimeout):
        return True
    if not isinstance(err, requests.exceptions.ConnectionError):
        return False
    seen = set()
    cur: Optional[BaseException] = err
    while cur is not None and id(cur) not in seen:
        seen.add(id(cur))
        text = f"{type(cur).__name__}: {cur}"
        if any(m in text for m in _CONNECT_PHASE_MARKERS):
            return True
        reason = getattr(cur, "reason", None)
        nxt = reason if isinstance(reason, BaseException) else None
        if nxt is None and cur.args and isinstance(cur.args[0], BaseException):
            nxt = cur.args[0]
        cur = nxt or cur.__cause__ or cur.__context__
    return False


def is_retryable(err: BaseException, policy: str) -> bool:
    if getattr(err, "retryable", False) is True:
        return True
    if isinstance(err, ApiError):
        if err.code in TERMINAL_API_CODES:
            return False
        if err.http == 429:
            return True
        if policy == "no-replay":
            return False
        if err.code in RETRYABLE_API_CODES:
            return policy != "no-999999"
        return err.http in RETRYABLE_HTTP_STATUS
    if isinstance(err, requests.exceptions.RequestException):
        if _is_connect_phase(err):
            return True
        if policy == "no-replay":
            return False
        return isinstance(
            err,
            (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.ChunkedEncodingError,
            ),
        )
    return False


def is_transient(err: BaseException) -> bool:
    """Anything the default policy would retry (for async polling loops)."""
    return is_retryable(err, "retry")


def parse_retry_after_ms(value: Optional[str], now_ms: Optional[float] = None) -> Optional[int]:
    """Retry-After as delta-seconds or an HTTP-date; None when missing or unparseable."""
    raw = (value or "").strip()
    if not raw:
        return None
    if raw.isdigit():
        return int(raw) * 1000
    try:
        parsed = email.utils.parsedate_to_datetime(raw)
    except (TypeError, ValueError, IndexError):
        return None
    if parsed is None:
        return None
    now = time.time() * 1000 if now_ms is None else now_ms
    return max(0, int(parsed.timestamp() * 1000 - now))


def backoff_ms(attempt: int, err: BaseException) -> float:
    retry_after = getattr(err, "retry_after_ms", None)
    if isinstance(retry_after, (int, float)) and retry_after >= 0:
        return min(float(retry_after), RETRY_AFTER_CEILING_MS)
    return min(MAX_DELAY_MS, BASE_DELAY_MS * 2 ** attempt + random.random() * BASE_DELAY_MS)


def _verbose() -> bool:
    return os.getenv("GANGTISE_VERBOSE", "").lower() in {"1", "true", "yes"}


def _header(headers: Any, name: str) -> Optional[str]:
    try:
        value = headers.get(name)
    except AttributeError:
        return None
    if isinstance(value, (list, tuple)):
        value = value[0] if value else None
    return str(value) if value is not None else None


def _parse_body(resp: Any, retry_after: Optional[int]) -> Any:
    try:
        return resp.json()
    except ValueError as exc:
        status = int(getattr(resp, "status_code", 0) or 0)
        message = f"API request failed (HTTP {status})" if status >= 400 else "Failed to parse API response"
        raise ApiError(
            message,
            http=status,
            body=str(getattr(resp, "text", "") or "")[:500],
            retry_after_ms=retry_after,
        ) from exc


def request_json(
    method: str,
    url: str,
    *,
    json: Any = None,
    params: Optional[Mapping[str, Any]] = None,
    timeout: int = 120,
    policy: Optional[RetryPolicy] = None,
    max_attempts: int = DEFAULT_RETRIES + 1,
    expect_data: bool = True,
) -> Any:
    resolved = policy or retry_policy_for_url(url)
    spec = match_endpoint(url)
    attempt = 0
    while True:
        try:
            resp = authorized_request(
                method,
                url,
                json=json,
                params=params,
                timeout=timeout,
            )
            retry_after = parse_retry_after_ms(_header(resp.headers, "Retry-After"))
            body = _parse_body(resp, retry_after)
            try:
                data = unwrap(body, http=resp.status_code, expect_data=expect_data)
            except ApiError as err:
                if err.retry_after_ms is None:
                    err.retry_after_ms = retry_after
                if resp.status_code == 429 and not err.code:
                    err.code = "999006"
                    err.hint = err.hint or hint_for(err.code, err.message)
                raise
            if spec and spec.item_failures:
                fail = fail_list_of(data)
                if fail:
                    raise PartialResultError(
                        f"部分失败 failList={fail}",
                        code=str((body or {}).get("code") or "000000"),
                        trace_id=str((body or {}).get("traceId") or ""),
                    )
            return data
        except PartialResultError:
            raise
        except (ApiError, requests.RequestException) as err:
            if attempt + 1 >= max_attempts or not is_retryable(err, resolved):
                raise
            delay = backoff_ms(attempt, err)
            if _verbose():
                print(
                    f"[gangtise] retry {attempt + 1}/{max_attempts - 1} in {int(delay)}ms: {err}",
                    file=sys.stderr,
                )
            time.sleep(delay / 1000.0)
            attempt += 1
