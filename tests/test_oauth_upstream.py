"""GTS_OAUTH_UPSTREAM 解析与转发头透传。"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

MCP_SRC = Path(__file__).resolve().parents[1] / "mcp" / "src"
if str(MCP_SRC) not in sys.path:
    sys.path.insert(0, str(MCP_SRC))

import oauth_server as oauth  # noqa: E402


def test_resolve_oauth_upstream_default(monkeypatch):
    monkeypatch.delenv("GTS_OAUTH_UPSTREAM", raising=False)
    monkeypatch.delenv("GTS_OAUTH_ISSUER", raising=False)
    assert oauth.resolve_oauth_upstream() == "https://auth.gangtise.com"


def test_resolve_oauth_upstream_prefers_explicit(monkeypatch):
    monkeypatch.setenv(
        "GTS_OAUTH_UPSTREAM",
        "http://workbuddy-connector-server.platform-business:15684/",
    )
    monkeypatch.setenv("GTS_OAUTH_ISSUER", "https://auth.gangtise.com")
    assert (
        oauth.resolve_oauth_upstream()
        == "http://workbuddy-connector-server.platform-business:15684"
    )


def test_resolve_oauth_upstream_falls_back_to_issuer(monkeypatch):
    monkeypatch.delenv("GTS_OAUTH_UPSTREAM", raising=False)
    monkeypatch.setenv("GTS_OAUTH_ISSUER", "https://auth.example/oauth2/")
    assert oauth.resolve_oauth_upstream() == "https://auth.example/oauth2"


def test_proxy_forward_headers_keep_ip_chain(monkeypatch):
    monkeypatch.setenv("GTS_CALLER", "mcp")

    class _Headers(dict):
        def get(self, key, default=None):
            target = key.lower()
            for k, v in self.items():
                if k.lower() == target:
                    return v
            return default

    class _Client:
        host = "10.68.1.2"

    class _Request:
        headers = _Headers(
            {
                "content-type": "application/x-www-form-urlencoded",
                "accept": "application/json",
                "x-forwarded-for": "203.0.113.8, 10.0.0.8",
                "x-real-ip": "203.0.113.8",
                "x-forwarded-proto": "https",
            }
        )
        client = _Client()

    headers = oauth._proxy_forward_headers(_Request())
    assert headers["X-Forwarded-For"] == "203.0.113.8, 10.0.0.8"
    assert headers["X-Real-IP"] == "203.0.113.8"
    assert headers["X-Forwarded-Proto"] == "https"
    assert headers["Content-Type"] == "application/x-www-form-urlencoded"
    assert headers.get("caller") == "mcp"


def test_external_as_endpoints_split_public_and_upstream(monkeypatch):
    monkeypatch.setenv("GTS_OAUTH_ISSUER", "https://auth.gangtise.com")
    monkeypatch.setenv(
        "GTS_OAUTH_UPSTREAM",
        "http://workbuddy-connector-server.platform-business:15684",
    )
    monkeypatch.setenv("GTS_OAUTH_RESOURCE", "https://open.gangtise.com/application/open-mcp")
    assert (
        oauth._external_as_public_endpoint(None, "/oauth/authorize")
        == "https://auth.gangtise.com/oauth/authorize"
    )
    assert (
        oauth._external_as_upstream_endpoint("/.well-known/openid-configuration")
        == "http://workbuddy-connector-server.platform-business:15684/.well-known/openid-configuration"
    )
