"""Single unwrap for Gangtise OpenAPI envelopes."""
from __future__ import annotations

from typing import Any, Mapping, Optional

from .errors import ApiError


OK_CODES = frozenset({"000000", "0", "200", ""})


def is_ok(body: Mapping[str, Any], *, http: int = 200) -> bool:
    if http and http >= 400:
        return False
    status = body.get("status")
    if status is False:
        return False
    state = body.get("state")
    if state is False or body.get("success") is False:
        return False
    code = str(body.get("code", "")).strip()
    if code and code not in OK_CODES:
        return False
    if status is True or state is True or body.get("success") is True:
        return True
    if code in OK_CODES:
        return True
    # some legacy payloads only have data
    return "data" in body and status is not False


def unwrap(
    body: Any,
    *,
    http: int = 200,
    expect_data: bool = True,
) -> Any:
    """Return `data` (or the whole body if unenveloped). Raise ApiError on failure."""
    if not isinstance(body, dict):
        if http and http >= 400:
            raise ApiError(f"API request failed (HTTP {http})", http=http, body=body)
        if expect_data:
            raise ApiError("响应不是 JSON 对象", http=http)
        return body
    trace_id = str(body.get("traceId") or body.get("trace_id") or "")
    code = str(body.get("code", "")).strip()
    msg = str(body.get("msg") or body.get("message") or body.get("error") or "")
    if not is_ok(body, http=http):
        if not msg and http and http >= 400:
            msg = f"API request failed (HTTP {http})"
        raise ApiError(
            msg or "API request failed",
            code=code,
            http=http,
            trace_id=trace_id,
            body=body,
        )
    if "data" in body:
        data = body.get("data")
        # EDE-style inner envelope: outer 000000, inner failure in data
        if isinstance(data, dict) and "code" in data and str(data.get("code", "")) not in OK_CODES:
            inner_msg = str(data.get("msg") or data.get("message") or msg or "inner envelope failed")
            raise ApiError(
                inner_msg,
                code=str(data.get("code", "")),
                http=http,
                trace_id=trace_id,
                body=body,
            )
        return data
    return body


def attach_trace(payload: Any, trace_id: str) -> Any:
    if trace_id and isinstance(payload, dict) and "traceId" not in payload:
        payload = dict(payload)
        payload["_traceId"] = trace_id
    return payload
