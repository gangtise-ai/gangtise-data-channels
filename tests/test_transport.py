from unittest.mock import MagicMock, patch

from gangtise_core.errors import ApiError, PartialResultError
from gangtise_core.transport import request_json
import pytest


def _json_resp(body, status=200, headers=None):
    resp = MagicMock()
    resp.status_code = status
    resp.headers = headers or {}
    resp.json.return_value = body
    resp.text = ""
    return resp


def test_request_json_points_insufficient_not_swallowed():
    resp = _json_resp({"code": "999005", "msg": "积分不足", "status": False, "traceId": "t-1"})
    with patch("gangtise_core.transport.authorized_request", return_value=resp):
        with pytest.raises(ApiError) as ei:
            request_json("POST", "https://openapi.gangtise.com/application/open-quote/kline/daily", json={})
    assert ei.value.code == "999005"
    assert ei.value.trace_id == "t-1"
    assert ei.value.exit_code == 1


def test_fail_list_is_partial_exit_3():
    resp = _json_resp(
        {
            "code": "000000",
            "status": True,
            "data": {"failList": [{"securityCode": "600519.SH", "msg": "已存在"}]},
        }
    )
    with patch("gangtise_core.transport.authorized_request", return_value=resp):
        with pytest.raises(PartialResultError) as ei:
            request_json(
                "POST",
                "https://openapi.gangtise.com/application/open-vault/stock-pool/addStock",
                json={},
            )
    assert ei.value.exit_code == 3


def test_no_replay_does_not_retry_5xx():
    resp = _json_resp({"code": "500001", "msg": "bad gateway", "status": False}, status=502)
    with patch("gangtise_core.transport.authorized_request", return_value=resp) as mocked:
        with pytest.raises(ApiError):
            request_json(
                "POST",
                "https://openapi.gangtise.com/application/ai/resource/download",
                json={},
            )
        assert mocked.call_count == 1


def test_retry_policy_retries_502_on_ordinary_endpoint():
    bad = _json_resp({"code": "500001", "msg": "bad gateway", "status": False}, status=502)
    ok = _json_resp({"code": "000000", "status": True, "data": {"fieldList": ["a"], "list": [[1]]}})
    with patch("gangtise_core.transport.authorized_request", side_effect=[bad, ok]) as mocked:
        with patch("gangtise_core.transport.time.sleep"):
            data = request_json(
                "POST",
                "https://openapi.gangtise.com/application/open-quote/kline/daily",
                json={},
            )
    assert mocked.call_count == 2
    assert data["fieldList"] == ["a"]


# ── Ported from gangtise-openapi-cli tests/unit/transport.test.ts ──

import requests
from urllib3.exceptions import NewConnectionError

from gangtise_core.transport import (
    RETRY_AFTER_CEILING_MS,
    backoff_ms,
    is_retryable,
    parse_retry_after_ms,
)

KLINE = "https://openapi.gangtise.com/application/open-quote/kline/daily"
EDE = "https://openapi.gangtise.com/application/open-indicator/EDE/time-series"
DOWNLOAD = "https://openapi.gangtise.com/application/ai/resource/download"


def _refused():
    inner = NewConnectionError(None, "Failed to establish a new connection: [Errno 61] Connection refused")
    return requests.exceptions.ConnectionError(inner)


@pytest.mark.parametrize(
    "err,policy,expected",
    [
        (ApiError("x", http=502), "retry", True),
        (ApiError("x", http=400), "retry", False),
        (ApiError("x", http=502), "no-replay", False),
        (ApiError("x", code="999999", http=200), "retry", True),
        (ApiError("x", code="999999", http=500), "no-999999", False),
        (ApiError("x", http=500), "no-999999", True),
        (ApiError("x", code="999999", http=500), "no-replay", False),
        (ApiError("x", code="140002", http=500), "retry", False),
        (ApiError("x", code="999011", http=503), "retry", False),
        (ApiError("x", code="999006", http=429), "no-replay", True),
        (ApiError("x", code="999006", http=500), "retry", True),
        (ApiError("x", code="999006", http=500), "no-replay", False),
        (requests.exceptions.ReadTimeout("read timed out"), "retry", True),
        (requests.exceptions.ReadTimeout("read timed out"), "no-replay", False),
        (requests.exceptions.ConnectTimeout("connect timed out"), "no-replay", True),
        (requests.exceptions.ConnectionError("Connection reset by peer"), "no-replay", False),
        (requests.exceptions.ConnectionError("Connection reset by peer"), "retry", True),
    ],
)
def test_retry_decision_matrix(err, policy, expected):
    assert is_retryable(err, policy) is expected


def test_connect_phase_refusal_retries_even_under_no_replay():
    assert is_retryable(_refused(), "no-replay") is True


def test_explicit_retryable_mark_wins():
    err = ApiError("token expired", code="0000001008", http=401)
    err.retryable = True
    assert is_retryable(err, "no-replay") is True


def test_parse_retry_after():
    assert parse_retry_after_ms("3") == 3000
    now = 1_000_000_000_000
    assert parse_retry_after_ms("Sun, 09 Sep 2001 01:46:45 GMT", now_ms=now) == 5000
    assert parse_retry_after_ms(None) is None
    assert parse_retry_after_ms("soon") is None


def test_backoff_honors_retry_after_but_caps_it():
    err = ApiError("slow down", http=429, retry_after_ms=1500)
    assert backoff_ms(0, err) == 1500
    err.retry_after_ms = 10 * 60 * 1000
    assert backoff_ms(0, err) == RETRY_AFTER_CEILING_MS


def test_backoff_default_is_jittered_exponential_under_4s():
    err = ApiError("x", http=502)
    for attempt in range(6):
        delay = backoff_ms(attempt, err)
        assert 400 * min(2 ** attempt, 10) <= delay + 1e-9 or delay == 4000
        assert delay <= 4000


def test_429_is_retried_on_no_replay_endpoint_with_retry_after():
    limited = _json_resp({"code": "999006", "msg": "限流", "status": False}, status=429, headers={"Retry-After": "2"})
    ok = _json_resp({"code": "000000", "status": True, "data": {"ok": 1}})
    with patch("gangtise_core.transport.authorized_request", side_effect=[limited, ok]) as mocked:
        with patch("gangtise_core.transport.time.sleep") as slept:
            assert request_json("GET", DOWNLOAD) == {"ok": 1}
    assert mocked.call_count == 2
    slept.assert_called_once_with(2.0)


def test_999999_not_retried_on_ede():
    resp = _json_resp({"code": 999999, "msg": "系统错误", "status": False}, status=500)
    with patch("gangtise_core.transport.authorized_request", return_value=resp) as mocked:
        with pytest.raises(ApiError) as ei:
            request_json("POST", EDE, json={})
    assert mocked.call_count == 1
    assert ei.value.code == "999999"


def test_999999_retried_on_default_endpoint_up_to_two_retries():
    resp = _json_resp({"code": "999999", "msg": "系统错误", "status": False})
    with patch("gangtise_core.transport.authorized_request", return_value=resp) as mocked:
        with patch("gangtise_core.transport.time.sleep"):
            with pytest.raises(ApiError):
                request_json("POST", KLINE, json={})
    assert mocked.call_count == 3


def test_140002_not_retried_even_on_http_500():
    resp = _json_resp({"code": "140002", "msg": "业务处理失败", "status": False}, status=500)
    with patch("gangtise_core.transport.authorized_request", return_value=resp) as mocked:
        with pytest.raises(ApiError):
            request_json("POST", KLINE, json={})
    assert mocked.call_count == 1


def test_non_json_5xx_is_an_http_error_and_retried():
    bad = MagicMock(status_code=503, headers={}, text="<html>unavailable</html>")
    bad.json.side_effect = ValueError("no json")
    ok = _json_resp({"code": "000000", "status": True, "data": [1]})
    with patch("gangtise_core.transport.authorized_request", side_effect=[bad, ok]) as mocked:
        with patch("gangtise_core.transport.time.sleep"):
            assert request_json("POST", KLINE, json={}) == [1]
    assert mocked.call_count == 2


def test_non_json_4xx_names_the_status():
    bad = MagicMock(status_code=404, headers={}, text="not found")
    bad.json.side_effect = ValueError("no json")
    with patch("gangtise_core.transport.authorized_request", return_value=bad):
        with pytest.raises(ApiError) as ei:
            request_json("POST", KLINE, json={})
    assert "HTTP 404" in str(ei.value)
    assert ei.value.exit_code == 2


def test_connect_refused_retried_on_no_replay_endpoint():
    ok = _json_resp({"code": "000000", "status": True, "data": {"ok": 1}})
    with patch("gangtise_core.transport.authorized_request", side_effect=[_refused(), ok]) as mocked:
        with patch("gangtise_core.transport.time.sleep"):
            assert request_json("GET", DOWNLOAD) == {"ok": 1}
    assert mocked.call_count == 2


def test_read_timeout_not_retried_on_no_replay_endpoint():
    with patch(
        "gangtise_core.transport.authorized_request",
        side_effect=requests.exceptions.ReadTimeout("read timed out"),
    ) as mocked:
        with pytest.raises(requests.exceptions.ReadTimeout):
            request_json("GET", DOWNLOAD)
    assert mocked.call_count == 1
