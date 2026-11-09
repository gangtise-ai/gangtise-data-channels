import pytest

pytest.importorskip("mcp")

import _use_generated  # noqa: F401,E402
from subpath_routing import (  # noqa: E402
    exposure_for_source,
    parse_subpaths,
    parse_subpaths_mode,
    progressive_subpath,
    progressive_subpaths,
    split_subpath,
)


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    monkeypatch.delenv("SUBPATHS", raising=False)
    monkeypatch.delenv("SUBPATHS_MODE", raising=False)
    monkeypatch.delenv("MCP_PROGRESSIVE_SUBPATH", raising=False)
    yield


def test_progressive_subpath_merged_into_parse_subpaths(monkeypatch):
    monkeypatch.setenv("SUBPATHS", "doubao,ali")
    monkeypatch.setenv("MCP_PROGRESSIVE_SUBPATH", "progressive")
    assert progressive_subpath() == "progressive"
    assert parse_subpaths() == ("doubao", "ali", "progressive")


def test_progressive_only_when_subpaths_empty(monkeypatch):
    monkeypatch.setenv("MCP_PROGRESSIVE_SUBPATH", "progressive")
    assert parse_subpaths() == ("progressive",)


def test_progressive_not_duplicated(monkeypatch):
    monkeypatch.setenv("SUBPATHS", "progressive,doubao")
    monkeypatch.setenv("MCP_PROGRESSIVE_SUBPATH", "progressive")
    assert parse_subpaths() == ("progressive", "doubao")


def test_subpaths_mode_parse_and_defaults(monkeypatch):
    monkeypatch.setenv("SUBPATHS", "A,B,C")
    monkeypatch.setenv("SUBPATHS_MODE", "A:leaf;B:progressive")
    assert parse_subpaths_mode() == {"A": "leaf", "B": "skill"}
    assert exposure_for_source("A") == "leaf"
    assert exposure_for_source("B") == "skill"
    assert exposure_for_source("C") == "leaf"  # 未声明默认 leaf
    assert exposure_for_source("") is None
    assert progressive_subpaths() == ("B",)
    assert parse_subpaths() == ("A", "B", "C")


def test_subpaths_mode_merges_names_into_parse_subpaths(monkeypatch):
    monkeypatch.setenv("SUBPATHS", "doubao")
    monkeypatch.setenv("SUBPATHS_MODE", "progressive:progressive")
    assert parse_subpaths() == ("doubao", "progressive")


def test_split_progressive_under_root():
    stripped, source = split_subpath(
        "/progressive/",
        mcp_base="/",
        subpaths=("progressive",),
    )
    assert stripped == "/"
    assert source == "progressive"


def test_split_progressive_under_open_mcp():
    stripped, source = split_subpath(
        "/open-mcp/progressive/sse",
        mcp_base="/open-mcp",
        subpaths=("doubao", "progressive"),
    )
    assert stripped == "/open-mcp/sse"
    assert source == "progressive"
