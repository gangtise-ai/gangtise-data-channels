import importlib
import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

SKILLS = Path(__file__).resolve().parents[1] / "skills" / "openapi"
_PACKAGES = {p.name.replace("-", "_") for p in SKILLS.iterdir() if (p / "scripts").is_dir()}


def _owned(key: str) -> bool:
    return key.split(".", 1)[0] in _PACKAGES


@pytest.fixture(autouse=True)
def _isolate_skill_packages():
    """生成的 CLI handler 包与 skill 包同名：测试前移走已缓存的同名模块，测试后原样恢复。"""
    saved = {k: v for k, v in sys.modules.items() if _owned(k)}
    for k in saved:
        del sys.modules[k]
    yield
    for k in [k for k in sys.modules if _owned(k)]:
        del sys.modules[k]
    sys.modules.update(saved)


def _load(skill: str, module: str):
    scripts = SKILLS / skill / "scripts"
    spec = importlib.util.spec_from_file_location(f"_launch_{skill.replace('-', '_')}", scripts / "_launch.py")
    launch = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(launch)
    pkg = launch._register_package(scripts)
    return pkg, importlib.import_module(f"{pkg}.{module}")


def test_partial_response_sets_exit_code_3():
    _, runtime = _load("gangtise-data", "gts_runtime")
    result = runtime.success_result("ok", {"state": "success", "data": [], "partial": "缺数据"})
    assert result.exit_code == 3
    assert result.markers["partial"] == "缺数据"


def test_row_billed_fetch_refuses_without_confirm():
    pkg, runtime = _load("gangtise-data", "gts_runtime")
    url = "https://x/application/open-insight/chief-opinion/getList"
    with patch(f"{pkg}.gts_runtime.request_json", return_value={"total": 500, "list": []}) as probe:
        with pytest.raises(runtime.ValidationError):
            runtime.guard_row_billed_fetch(url, {}, 200)
        runtime.guard_row_billed_fetch(url, {}, 200, confirm=True)
    assert probe.call_count == 1
    assert probe.call_args.kwargs["json"]["size"] == 1


@pytest.mark.parametrize("value", ["0", "false", "OFF", "no"])
def test_credit_guard_can_be_disabled_by_env(monkeypatch, value):
    pkg, runtime = _load("gangtise-data", "gts_runtime")
    _, get_file = _load("gangtise-file", "get_file")
    monkeypatch.setenv("GANGTISE_CREDIT_GUARD", value)
    url = "https://x/application/open-insight/chief-opinion/getList"
    with patch(f"{pkg}.gts_runtime.request_json") as probe:
        runtime.guard_row_billed_fetch(url, {}, 5000)
    assert probe.call_count == 0
    get_file.guard_opinion_detail_download(500, False)


def test_credit_guard_on_by_default(monkeypatch):
    _, get_file = _load("gangtise-file", "get_file")
    monkeypatch.delenv("GANGTISE_CREDIT_GUARD", raising=False)
    with pytest.raises(get_file.ValidationError):
        get_file.guard_opinion_detail_download(500, False)


def test_row_billed_fetch_passes_when_total_is_small():
    pkg, runtime = _load("gangtise-data", "gts_runtime")
    url = "https://x/application/open-insight/chief-opinion/getList"
    with patch(f"{pkg}.gts_runtime.request_json", return_value={"total": 10, "list": []}):
        runtime.guard_row_billed_fetch(url, {}, 200)


def test_stockpool_delete_requires_confirm():
    _, stockpool = _load("gangtise-private", "stockpool")
    _, runtime = _load("gangtise-private", "gts_runtime")
    with pytest.raises(runtime.ValidationError):
        stockpool.stockpool_finder(mode="delete", pool_ids="1")


@pytest.mark.parametrize(
    "module, finder, id_kw, get_fn",
    [
        ("private_meeting", "private_meeting_finder", "conference_ids", "private_meeting_get"),
        ("private_record", "private_record_finder", "record_ids", "private_record_get"),
    ],
)
def test_private_finder_with_ids_dispatches_to_get(module, finder, id_kw, get_fn):
    pkg, mod = _load("gangtise-private", module)
    with patch(f"{pkg}.{module}.{get_fn}", return_value="got") as get:
        assert getattr(mod, finder)(**{id_kw: "abc123", "limit": 5}) == "got"
    assert get.call_args.kwargs[id_kw] == ["abc123"]


@pytest.mark.parametrize("skill", ["gangtise-file", "gangtise-kb"])
def test_download_flag_parses_bool_text(skill):
    import argparse

    _, utils = _load(skill, "utils")
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", type=utils.parse_bool_flag, nargs="?", const=True, default=False)
    assert parser.parse_args([]).d is False
    assert parser.parse_args(["-d"]).d is True
    assert parser.parse_args(["-d", "true"]).d is True
    assert parser.parse_args(["-d", "False"]).d is False
    assert parser.parse_args(["-d", "0"]).d is False
    with pytest.raises(SystemExit):
        parser.parse_args(["-d", "maybe"])


def test_opinion_details_batch_and_report_missing():
    pkg, get_file = _load("gangtise-file", "get_file")
    ids = [str(i) for i in range(25)] + ["3"]

    def fake(method, url, json=None, timeout=None):
        batch = json["chiefOpinionIdList"]
        return [{"chiefOpinionId": x, "content": x} for x in batch if x != "7"] + [{"chiefOpinionId": "999"}]

    with patch(f"{pkg}.get_file.request_json", side_effect=fake) as sent:
        got = get_file._fetch_opinion_details(ids, "首席观点", {})
    assert sent.call_count == 2
    assert [len(c.kwargs["json"]["chiefOpinionIdList"]) for c in sent.call_args_list] == [20, 5]
    assert "999" not in got["records"]
    assert got["missing"] == ["7"]
    assert len(got["records"]) == 24


def test_company_indicator_calendar_type_and_params():
    _, ci = _load("gangtise-data", "company_indicator")
    _, runtime = _load("gangtise-data", "gts_runtime")
    trade = {"parameterList": [{"paramKey": "tradeDate"}]}
    period = {"parameterList": [{"paramKey": "tradeDate"}, {"paramKey": "reportDate"}]}
    assert ci._auto_calendar_type({"a": trade}, ["a"]) == "TD"
    assert ci._auto_calendar_type({"a": trade, "b": period}, ["a", "b"]) is None
    assert ci._auto_calendar_type({"a": trade, "b": None}, ["a", "b"]) is None
    assert ci._parse_date_param("20260107", "x") == "2026-01-07"
    with pytest.raises(runtime.ValidationError):
        ci._parse_date_param("01-07-2026", "x")
    with pytest.raises(runtime.ValidationError):
        ci._build_request_options({"qte_closee": {"adjustType": "1"}}, ["qte_close"])


def test_quote_weekday_shards_and_trading_days():
    _, quote = _load("gangtise-data", "quote")
    assert quote._estimate_trading_days("2026-10-05", "2026-10-11") == 5
    assert quote._weekday_shards("2026-10-09", "2026-10-13", 1) == [
        ("2026-10-09", "2026-10-09"),
        ("2026-10-12", "2026-10-12"),
        ("2026-10-13", "2026-10-13"),
    ]
    assert quote._weekday_shards("2026-10-09", "2026-10-13", 2) == [
        ("2026-10-09", "2026-10-12"),
        ("2026-10-13", "2026-10-13"),
    ]
    assert quote._weekday_shards("2026-10-10", "2026-10-11", 1) == []


def test_quote_groups_securities_to_fit_row_cap():
    pkg, quote = _load("gangtise-data", "quote")
    codes = [f"{i:06d}.SH" for i in range(100)]
    payload = {"startDate": "2025-01-01", "endDate": "2025-12-31"}
    sizes = []

    def fake(url, headers, body):
        sizes.append(len(body["securityList"]))
        rows = body["limit"] if body["securityList"][0] == "000000.SH" else 3
        return pd.DataFrame({"securityCode": [body["securityList"][0]] * rows}), None

    with patch(f"{pkg}.quote._fetch_kline_data", side_effect=fake):
        frames, errors, truncated = quote._fetch_daily_by_security_groups({}, payload, codes, None)
    days = quote._estimate_trading_days("2025-01-01", "2025-12-31")
    assert max(sizes) * days < quote.QUOTE_MAX_LIMIT
    assert sum(sizes) == 100
    assert errors == []
    assert truncated[0] == "000000.SH"


def test_quote_late_start_note_per_security():
    _, quote = _load("gangtise-data", "quote")
    data = pd.DataFrame({"证券代码": ["A", "A", "B"], "日期": ["2026-01-05", "2026-01-06", "2026-03-02"]})
    note = quote._late_start_note(data, "2026-01-01", per_security=True)
    assert note and "B" in note and "A " not in note


def test_file_title_strips_path_separator():
    _, get_file = _load("gangtise-file", "get_file")
    assert "/" not in get_file.safe_file_title({"title": "Week Ending 9/26/2026", "url": ""})


def test_calendar_maps_cn_values_and_industries():
    _, cal = _load("gangtise-file", "investment_calendar")
    payload = cal._build_payload(
        "roadshow", None, None, None, None, None, None, ["港股"], ["专家"], None, None, None
    )
    assert payload["marketList"] == ["hkStocks"]
    assert payload["participantRoleList"] == ["expert"]
    assert cal._resolve_research_areas(["电新", "策略"]) == ["100800111", "122000002"]
    with pytest.raises(cal.ValidationError):
        cal._resolve_research_areas(["不存在的行业xyz"])


def test_opinion_splits_research_areas_and_industries():
    _, opinion = _load("gangtise-file", "opinion")
    areas, inds, unknown = opinion._resolve_research_areas(["宏观", "电新", "不存在的行业xyz"])
    assert areas == ["122000001"]
    assert inds == ["100800111"]
    assert unknown == ["不存在的行业xyz"]


def test_opinion_resolves_category_llm_broker_tags():
    _, opinion = _load("gangtise-file", "opinion")
    assert len(opinion.OPINION_LLM_CODES) == 28
    assert opinion._resolve_categories(["业绩点评", "industryAnalysis"]) == [
        "earningsReview",
        "industryAnalysis",
    ]
    assert opinion._resolve_broker_tags(["头部券商", "newFortune"]) == [
        "topBroker",
        "newFortune",
    ]
    assert opinion._resolve_llm_tags(["强烈推荐", "独供", "moat"]) == [
        "strongRcmd",
        "soleSupplier",
        "moat",
    ]
    assert opinion._display_codes(
        ["earningsReview", "topBroker"],
        {**opinion.OPINION_CATEGORY_LABEL_BY_CODE, **opinion.OPINION_BROKER_TAG_LABEL_BY_CODE},
    ) == "业绩点评, 头部券商"
    row = {
        "title": "t",
        "brief": "b",
        "author": {},
        "categoryList": ["earningsReview"],
        "llmTagList": ["strongRcmd", "beatExpect"],
        "brokerTagList": ["topBroker"],
        "chiefOpinionId": "1",
    }
    item = opinion._format_opinion_item([row])[0]
    assert item["观点类别"] == "业绩点评"
    assert item["投研业务标签"] == "强烈推荐, 超预期"
    assert item["机构标签"] == "头部券商"
    assert "标签" not in item


def test_industry_indicator_default_start_follows_end_date():
    _, ind = _load("gangtise-data", "industry_indicator")
    assert ind._default_dates(None, "2025-06-30") == ("2024-06-30", "2025-06-30")


def test_financial_margin_field_list_uses_api_safe_deps():
    """毛利率/净利率为本地衍生指标，fieldList 只能带接口合法短名，不能带 operatingRevenue 等长名。"""
    _, fin = _load("gangtise-data", "financial")
    api, margins, requested = fin._prepare_field_list(
        ["营业收入", "毛利率", "净利率"], "income", "a_share"
    )
    assert margins == {"grossProfitMargin", "netProfitMargin"}
    assert requested == ["opRev", "grossProfitMargin", "netProfitMargin"]
    assert set(api) == {"opRev", "opCost", "netProfit"}
    assert "operatingRevenue" not in api and "operatingCost" not in api
    api_only, margins_only, _ = fin._prepare_field_list(["毛利率"], "income", "a_share")
    assert margins_only == {"grossProfitMargin"}
    assert set(api_only) == {"opRev", "opCost"}
    hk_api, _, _ = fin._prepare_field_list(["净利率"], "income", "hk")
    assert set(hk_api) == {"opRev", "netProfit"}


def test_private_record_finder_normalizes_cn_filters():
    pkg, rec = _load("gangtise-private", "private_record")
    with patch(f"{pkg}.private_record.private_record_search", return_value="ok") as search:
        rec.private_record_finder(category_list=["手机录音"], space_type_list=["我的速记"])
    kwargs = search.call_args.kwargs
    assert kwargs["category_list"] == ["mobile"]
    assert kwargs["space_type_list"] == [1]


def test_security_clue_industry_alias_searches_sw_index():
    pkg, clue = _load("gangtise-agent", "security_clue")
    search = MagicMock(return_value={"state": "error", "message": "x", "data": [], "usage": {}})
    with patch(f"{pkg}.security_clue.security_search_basic", search), \
         patch(f"{pkg}.security_clue.format_response", return_value="err"):
        clue.run_security_clue_list(query_mode="行业", securities=["电力设备"])
    args, kwargs = search.call_args
    assert args[0] == "申万电力设备"
    assert kwargs["category"] == ["index"]


def test_wechat_message_filters_without_groups_fetch_messages():
    pkg, wm = _load("gangtise-private", "wechat_message")
    with patch(f"{pkg}.wechat_message.wechat_message_get", return_value="get") as get, \
         patch(f"{pkg}.wechat_message.wechat_message_search", return_value="search") as search:
        assert wm.wechat_message_finder(keyword="半导体", start_time="2026-09-01") == "get"
        assert wm.wechat_message_finder(keyword="半导体", mode="get") == "get"
        assert wm.wechat_message_finder(keyword="投研群") == "search"
    assert get.call_args.kwargs["wechat_group_id_list"] is None
    assert search.call_count == 1


def test_kb_download_falls_back_to_generic_on_404():
    pkg, gf = _load("gangtise-kb", "get_file")
    calls = []

    def fake(method, url, **kw):
        calls.append((url, kw["params"]))
        return MagicMock(status_code=404 if "broker-report" in url else 200)

    with patch(f"{pkg}.get_file.authorized_request", side_effect=fake):
        resp = gf._request_download("178724130470891523", "研究报告", "pdf", {})
    assert resp.status_code == 200
    assert calls[-1][1] == {"sourceId": "178724130470891523", "resourceType": 10}


def test_earnings_period_normalized_to_api_enum():
    _, agents = _load("gangtise-agent", "agents")
    norm = agents.normalize_earnings_period
    assert norm("2026q1") == "2026q1"
    assert norm("2026Q2") == "2026interim"
    assert norm("2026h1") == "2026interim"
    assert norm("2026中报") == "2026interim"
    assert norm("2025q4") == "2025annual"
    assert norm("2025年报") == "2025annual"
    assert norm("2026INTERIM") == "2026interim"
    with pytest.raises(ValueError):
        norm("interim")


def test_kb_hk_announcement_strips_suffix():
    pkg, gf = _load("gangtise-kb", "get_file")
    with patch(f"{pkg}.get_file.authorized_request", return_value=MagicMock(status_code=200)) as req:
        gf._request_download("15742322-0", "港股公告", "pdf", {})
    assert "announcement-hk/download/file" in req.call_args.args[1]
    assert req.call_args.kwargs["params"] == {"announcementId": "15742322"}


def test_quote_adjust_uses_cumulative_factor_independent_of_window():
    _, q = _load("gangtise-data", "quote")
    data = pd.DataFrame({
        "证券代码": ["600519.SH"] * 2,
        "日期": ["2025-06-25", "2025-06-27"],
        "开盘价": [100.0, 100.0], "最高价": [100.0, 100.0], "最低价": [100.0, 100.0],
        "收盘价": [100.0, 100.0], "昨收价": [100.0, 100.0],
    })
    factors = pd.DataFrame({
        "securityCode": ["600519.SH"] * 2,
        "tradeDate": ["2025-06-25", "2025-06-27"],
        "adjustFactor": [8.0, 8.5],
    })
    hfq, _, _ = q._apply_daily_adjust_with_factors(data, factors, "backward")
    assert list(hfq["收盘价(后复权)"]) == [800.0, 850.0]
    qfq, _, _ = q._apply_daily_adjust_with_factors(data, factors, "forward", {"600519.SH": 10.0})
    assert list(qfq["收盘价(前复权)"]) == [80.0, 85.0]
    qfq_window, _, _ = q._apply_daily_adjust_with_factors(data, factors, "forward")
    assert list(qfq_window["收盘价(前复权)"]) == [94.12, 100.0]
