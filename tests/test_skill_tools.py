import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("mcp")

import _use_generated  # noqa: F401,E402
import skill_tools  # noqa: E402
import url_whitelist  # noqa: E402
from catalog import load_catalog  # noqa: E402

load_catalog()


@pytest.fixture(autouse=True)
def _allow_all(monkeypatch):
    monkeypatch.setattr(skill_tools, "get_white_list", lambda: set())
    monkeypatch.setattr(skill_tools, "tool_denied_reason", lambda name, wl=None: None)
    monkeypatch.delenv("MCP_TOOL_EXPOSURE", raising=False)
    monkeypatch.delenv("MCP_TOOL_BLACKLIST", raising=False)
    url_whitelist.get_tool_blacklist(force=True)
    yield
    url_whitelist.get_tool_blacklist(force=True)


def _call(name, arguments):
    return asyncio.run(skill_tools.call_tool(name, arguments, attach=False))


def _text(result):
    content = getattr(result, "content", result)
    return "".join(getattr(c, "text", "") for c in content)


def _is_error(result):
    return bool(getattr(result, "is_error", None) or getattr(result, "isError", False))


def _schema(tool):
    return getattr(tool, "input_schema", None) or tool.inputSchema


def test_catalog_has_new_skills_without_conflicts():
    cat = load_catalog()
    assert cat.errors == {}
    for label in ("gangtise-fund", "gangtise-bond", "gangtise-web"):
        assert label in cat.skills
    assert cat.resolve_function("gangtise-fund", "nav") == "fund_nav"
    assert cat.resolve_function("gangtise-bond", "quote") == "bond_quote"
    assert cat.resolve_function("gangtise-data", "quote") == "quote"
    assert cat.resolve_function("gangtise-web", "web_search") == "web_search"
    for info in cat.skills.values():
        assert info.summary
        for flat in info.functions.values():
            assert flat in cat.spec_map, flat


def test_skill_exposure_lists_only_skills(monkeypatch):
    monkeypatch.setenv("MCP_TOOL_EXPOSURE", "skill")
    cat = load_catalog()
    tools = skill_tools.list_tools()
    names = [t.name for t in tools]
    assert names == ["get_job_result", *cat.skills]
    file_tool = next(t for t in tools if t.name == "gangtise-file")
    enum = _schema(file_tool)["properties"]["function"]["enum"]
    assert enum[0] == "help"
    assert "report" in enum and "get_file" in enum


def test_default_exposure_is_leaf():
    names = {t.name for t in skill_tools.list_tools()}
    assert {"get_job_result", "fund_nav", "bond_quote", "quote", "web_search"} <= names
    assert "gangtise-fund" not in names


def test_skill_without_function_returns_all_function_docs():
    result = _call("gangtise-fund", {})
    assert not _is_error(result)
    text = _text(result)
    assert text.startswith("# gangtise-fund")
    for fn in load_catalog().skills["gangtise-fund"].functions:
        assert f"### {fn}" in text
    assert "`securities` (array<string>" in text
    assert _text(_call("gangtise-fund", {"function": "help"})) == text


def test_missing_required_argument_returns_usage():
    result = _call("gangtise-web", {"function": "web_search", "arguments": {}})
    assert _is_error(result)
    payload = json.loads(_text(result))
    assert payload["code"] == "INVALID_PARAMS"
    assert "缺少必填参数: query" in payload["message"]
    assert "### web_search" in payload["message"]


def test_unknown_function_and_unknown_argument():
    result = _call("gangtise-bond", {"function": "nope"})
    assert json.loads(_text(result))["code"] == "UNKNOWN_TOOL"
    result = _call("gangtise-web", {"function": "web_search", "arguments": {"query": "x", "bogus": 1}})
    payload = json.loads(_text(result))
    assert payload["code"] == "INVALID_PARAMS"
    assert "bogus" in payload["message"]


def _web_response():
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "code": "000000",
        "status": True,
        "data": {
            "total": 1,
            "list": [
                {"title": "央行公告", "url": "https://www.pbc.gov.cn/a", "summary": "摘要", "tier": "T0"}
            ],
        },
    }
    return resp


@pytest.mark.parametrize(
    "arguments",
    [
        {"function": "web_search", "arguments": {"query": "央行 降准", "site_list": ["pbc.gov.cn"], "size": "3"}},
        {"function": "web_search", "arguments": json.dumps({"query": "央行 降准", "site_list": "pbc.gov.cn", "size": 3})},
        {"function": "web_search", "query": "央行 降准", "site_list": "pbc.gov.cn", "size": 3},
    ],
)
def test_skill_call_dispatches_to_script(arguments):
    with patch("gangtise_web.web_search.get_authorization_token", return_value="token"), patch(
        "gangtise_web.web_search.authorized_request", return_value=_web_response()
    ) as req:
        result = _call("gangtise-web", arguments)
    assert not _is_error(result), _text(result)
    assert "央行公告" in _text(result)
    sent = req.call_args.kwargs["json"]
    assert sent["query"] == "央行 降准"
    assert sent["size"] == 3
    assert "pbc.gov.cn" in json.dumps(sent)


def test_leaf_name_still_callable():
    with patch("gangtise_web.web_search.get_authorization_token", return_value="token"), patch(
        "gangtise_web.web_search.authorized_request", return_value=_web_response()
    ):
        result = _call("web_search", {"query": "央行 降准"})
    assert not _is_error(result)


def test_blacklisted_skill_is_hidden_and_forbidden(monkeypatch):
    monkeypatch.setenv("MCP_TOOL_EXPOSURE", "skill")
    monkeypatch.setenv("MCP_TOOL_BLACKLIST", "gangtise-web,fund_nav")
    url_whitelist.get_tool_blacklist(force=True)
    monkeypatch.setattr(skill_tools, "tool_denied_reason", url_whitelist.tool_denied_reason)
    names = [t.name for t in skill_tools.list_tools()]
    assert "gangtise-web" not in names
    fund = next(t for t in skill_tools.list_tools() if t.name == "gangtise-fund")
    assert "nav" not in _schema(fund)["properties"]["function"]["enum"]
    assert json.loads(_text(_call("gangtise-web", {"function": "web_search"})))["code"] == "FORBIDDEN"
    assert json.loads(_text(_call("gangtise-fund", {"function": "nav"})))["code"] == "FORBIDDEN"
