from unittest.mock import MagicMock

from gangtise_core import auth


def test_resolve_client_ip_priority_and_chain():
    assert auth.resolve_client_ip({"X-Forwarded-For": "203.0.113.8, 10.0.0.8"}) == "203.0.113.8"
    assert auth.resolve_client_ip({"X-Forwarded-For": "unknown", "Proxy-Client-IP": "203.0.113.9"}) == "203.0.113.9"
    assert (
        auth.resolve_client_ip(
            {
                "Proxy-Client-IP": "unknown",
                "WL-Proxy-Client-IP": "",
                "HTTP_CLIENT_IP": "203.0.113.7",
            }
        )
        == "203.0.113.7"
    )
    assert auth.resolve_client_ip({"HTTP_X_FORWARDED_FOR": "198.51.100.4, 10.1.1.1"}) == "198.51.100.4"
    assert auth.resolve_client_ip({}, remote_addr="192.0.2.10") == "192.0.2.10"
    assert auth.resolve_client_ip({"X-Forwarded-For": "unknown"}, remote_addr="192.0.2.10") == "192.0.2.10"
    assert auth.resolve_client_ip({"x-forwarded-for": "2001:db8::1"}) == "2001:db8::1"
    assert auth.resolve_client_ip({}) == ""


def test_authorized_request_forwards_client_ip(monkeypatch):
    token = auth.set_request_client_ip("203.0.113.10")
    captured = {}

    def fake_request(method, url, headers=None, timeout=None, **kwargs):
        captured["headers"] = headers
        resp = MagicMock()
        resp.status_code = 200
        return resp

    monkeypatch.setattr(auth.requests, "request", fake_request)
    monkeypatch.setattr(auth, "get_authorization_headers", lambda: {"Authorization": "Bearer t"})
    try:
        auth.authorized_request("GET", "http://down.example/x", retry_on_auth=False)
    finally:
        auth.reset_request_client_ip(token)
    assert captured["headers"]["X-Forwarded-For"] == "203.0.113.10"


def test_authorized_request_keeps_explicit_forwarded_for(monkeypatch):
    token = auth.set_request_client_ip("203.0.113.10")

    def fake_request(method, url, headers=None, timeout=None, **kwargs):
        fake_request.headers = headers
        resp = MagicMock()
        resp.status_code = 200
        return resp

    monkeypatch.setattr(auth.requests, "request", fake_request)
    monkeypatch.setattr(auth, "get_authorization_headers", lambda: {})
    try:
        auth.authorized_request(
            "GET",
            "http://down.example/x",
            headers={"X-Forwarded-For": "198.51.100.1"},
            retry_on_auth=False,
        )
    finally:
        auth.reset_request_client_ip(token)
    assert fake_request.headers["X-Forwarded-For"] == "198.51.100.1"


def test_authorized_request_sets_caller_when_configured(monkeypatch):
    monkeypatch.setenv("GTS_CALLER", "mcp")

    def fake_request(method, url, headers=None, timeout=None, **kwargs):
        fake_request.headers = headers
        resp = MagicMock()
        resp.status_code = 200
        return resp

    monkeypatch.setattr(auth.requests, "request", fake_request)
    monkeypatch.setattr(auth, "get_authorization_headers", lambda: {})
    auth.authorized_request("GET", "http://down.example/x", retry_on_auth=False)
    assert fake_request.headers["caller"] == "mcp"


def test_authorized_request_omits_header_without_client_ip(monkeypatch):
    def fake_request(method, url, headers=None, timeout=None, **kwargs):
        fake_request.headers = headers
        resp = MagicMock()
        resp.status_code = 200
        return resp

    monkeypatch.setattr(auth.requests, "request", fake_request)
    monkeypatch.setattr(auth, "get_authorization_headers", lambda: {})
    auth.authorized_request("GET", "http://down.example/x", retry_on_auth=False)
    assert "X-Forwarded-For" not in fake_request.headers
    assert not any(k.lower() == "x-forwarded-for" for k in fake_request.headers)
