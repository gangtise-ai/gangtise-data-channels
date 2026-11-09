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


def test_stockpool_search_defaults_to_personal_space(tmp_path):
    pkg, stockpool = _load("gangtise-private", "stockpool")
    pools = [{"poolId": "808477293", "poolName": "自选股1", "spaceType": 1}]
    with patch(f"{pkg}.stockpool._require_auth"), patch(f"{pkg}.stockpool._post", return_value=pools) as post:
        text = stockpool.stockpool_finder(mode="search", limit=10, output_dir=str(tmp_path))
    assert post.call_args.args[0] == stockpool.GET_POOL_LIST_URL
    assert post.call_args.args[1] == {"spaceType": 1}
    assert "个人自选股" in str(text)
    assert "808477293" in str(text)


def test_stockpool_get_uses_same_space_as_pool_ids(tmp_path):
    pkg, stockpool = _load("gangtise-private", "stockpool")
    stocks = [{"securityCode": "600519.SH", "securityName": "贵州茅台"}]
    with patch(f"{pkg}.stockpool._require_auth"), patch(f"{pkg}.stockpool._post", return_value=stocks) as post:
        text = stockpool.stockpool_finder(
            mode="get", pool_ids="908477301,908477302", space_type="租户", output_dir=str(tmp_path)
        )
    assert post.call_args.args[0] == stockpool.GET_STOCK_LIST_URL
    assert post.call_args.args[1] == {"spaceType": 2, "poolIdList": ["908477301", "908477302"]}
    assert "所属租户" in str(text)


def test_stockpool_all_tenant_pools():
    pkg, stockpool = _load("gangtise-private", "stockpool")
    with patch(f"{pkg}.stockpool._require_auth"), patch(f"{pkg}.stockpool._post", return_value=[]) as post:
        text = stockpool.stockpool_finder(all_pools=True, space_type=2)
    assert post.call_args.args[1] == {"spaceType": 2, "poolIdList": ["all"]}
    assert "所属租户" in str(text)


def test_stockpool_name_resolve_stays_in_requested_space(tmp_path):
    pkg, stockpool = _load("gangtise-private", "stockpool")

    def fake_post(url, payload):
        if url == stockpool.GET_POOL_LIST_URL:
            assert payload == {"spaceType": 2}
            return [{"poolId": "908477301", "poolName": "交易池", "spaceType": 2}]
        assert url == stockpool.GET_STOCK_LIST_URL
        assert payload == {"spaceType": 2, "poolIdList": ["908477301"]}
        return [{"securityCode": "600519.SH", "securityName": "贵州茅台"}]

    with patch(f"{pkg}.stockpool._require_auth"), patch(f"{pkg}.stockpool._post", side_effect=fake_post):
        text = stockpool.stockpool_finder(pool_ids="交易池", space_type="2", output_dir=str(tmp_path))
    assert "600519.SH" in str(text)


def test_stockpool_manage_rejects_tenant_space():
    _, stockpool = _load("gangtise-private", "stockpool")
    _, runtime = _load("gangtise-private", "gts_runtime")
    with pytest.raises(runtime.ValidationError, match="个人自选股"):
        stockpool.stockpool_finder(mode="create", pool_name="核心持仓", space_type=2)


@pytest.mark.parametrize("raw", [3, "3", "ALL", True])
def test_stockpool_rejects_invalid_space_type(raw):
    _, stockpool = _load("gangtise-private", "stockpool")
    _, runtime = _load("gangtise-private", "gts_runtime")
    with pytest.raises(runtime.ValidationError, match="space_type"):
        stockpool.stockpool_finder(mode="search", space_type=raw)


def test_stockpool_file_space_type_must_be_single_region(tmp_path):
    _, stockpool = _load("gangtise-private", "stockpool")
    _, runtime = _load("gangtise-private", "gts_runtime")
    path = tmp_path / "pools.csv"
    path.write_text("pool_id,pool_name,space_type\n908477301,交易池,2\n", encoding="utf-8")
    ids, space = stockpool._load_pools_from_file(str(path))
    assert ids == ["908477301"]
    assert space == 2
    mixed = tmp_path / "mixed.csv"
    mixed.write_text("pool_id,space_type\n1,1\n2,2\n", encoding="utf-8")
    with pytest.raises(runtime.ValidationError, match="space_type"):
        stockpool._load_pools_from_file(str(mixed))


def test_stockpool_delete_note_requires_confirm():
    _, stockpool = _load("gangtise-private", "stockpool")
    _, runtime = _load("gangtise-private", "gts_runtime")
    with pytest.raises(runtime.ValidationError, match="个股笔记"):
        stockpool.stockpool_finder(mode="delete_note", note_ids="1835")


def test_stockpool_search_note_all(tmp_path):
    pkg, stockpool = _load("gangtise-private", "stockpool")
    payload = {
        "total": 1,
        "list": [
            {
                "stockNoteId": "1740",
                "securityList": ["600111.SH", "688106.SH"],
                "content": "上游材料涨价",
                "createTime": "2026-10-23 10:20:03",
                "updateTime": "2026-10-23 11:05:00",
            }
        ],
    }
    with patch(f"{pkg}.stockpool._require_auth"), patch(f"{pkg}.stockpool._post", return_value=payload) as post:
        text = stockpool.stockpool_finder(mode="search_note", all_notes=True, output_dir=str(tmp_path))
    assert post.call_args.args[0] == stockpool.GET_NOTE_LIST_URL
    assert post.call_args.args[1] == {"from": 0, "size": 20, "securityList": ["all"]}
    assert "1740" in str(text)
    assert "上游材料涨价" in str(text)


def test_stockpool_search_note_by_ids_and_securities_mutex():
    _, stockpool = _load("gangtise-private", "stockpool")
    _, runtime = _load("gangtise-private", "gts_runtime")
    with pytest.raises(runtime.ValidationError, match="不能同时"):
        stockpool.stockpool_finder(mode="search_note", note_ids="1737", securities=["688106.SH"])


def test_stockpool_add_note_posts_payload():
    pkg, stockpool = _load("gangtise-private", "stockpool")
    with patch(f"{pkg}.stockpool._require_auth"), patch(
        f"{pkg}.stockpool._post", return_value={"stockNoteId": "1835", "securityList": ["688106.SH"]}
    ) as post:
        text = stockpool.stockpool_finder(
            mode="add_note", securities=["688106.SH"], note_content="电子特气国产替代"
        )
    assert post.call_args.args[0] == stockpool.ADD_NOTE_URL
    assert post.call_args.args[1] == {"securityList": ["688106.SH"], "content": "电子特气国产替代"}
    assert "1835" in str(text)


def test_stockpool_update_note_single_id():
    pkg, stockpool = _load("gangtise-private", "stockpool")
    _, runtime = _load("gangtise-private", "gts_runtime")
    with pytest.raises(runtime.ValidationError, match="一个笔记"):
        stockpool.stockpool_finder(mode="update_note", note_ids="1,2", note_content="x")
    with patch(f"{pkg}.stockpool._require_auth"), patch(f"{pkg}.stockpool._post", return_value={}) as post:
        text = stockpool.stockpool_finder(mode="update_note", note_ids="1835", note_content="终稿")
    assert post.call_args.args[0] == stockpool.UPDATE_NOTE_URL
    assert post.call_args.args[1] == {"stockNoteId": "1835", "content": "终稿"}
    assert "1835" in str(text)


def test_stockpool_delete_note_item_failures():
    pkg, stockpool = _load("gangtise-private", "stockpool")
    data = {
        "successList": ["1835"],
        "failList": [{"stockNoteId": "1836", "failReason": "笔记删除失败，请重试"}],
    }
    with patch(f"{pkg}.stockpool._require_auth"), patch(f"{pkg}.stockpool._post", return_value=data) as post:
        text = stockpool.stockpool_finder(mode="delete_note", note_ids="1835,1836", confirm=True)
    assert post.call_args.args[0] == stockpool.DELETE_NOTE_URL
    assert post.call_args.args[1] == {"stockNoteIdList": ["1835", "1836"]}
    assert "1835" in str(text) and "1836" in str(text)


def test_fund_flow_sector_resolves_id_and_fields(tmp_path):
    pkg, fund_flow = _load("gangtise-data", "fund_flow")
    api = {
        "total": 1,
        "fieldList": ["sectorId", "tradeDate", "sectorMainNetInflow"],
        "list": [["1000001065", "2024-05-20", 268000000.0]],
    }
    with patch(f"{pkg}.fund_flow.get_authorization_token", return_value="tok"), patch(
        f"{pkg}.fund_flow.get_authorization_headers", return_value={"Authorization": "tok"}
    ), patch(f"{pkg}.gts_runtime.request_json", return_value=api) as req:
        text = fund_flow.fund_flow_data(
            sectors=["1000001065"],
            start_date="2024-05-20",
            end_date="2024-05-20",
            field_list=["mainNetInflow"],
            output_dir=str(tmp_path),
        )
    assert req.call_args.args[0] == "POST"
    assert req.call_args.args[1] == fund_flow.FUND_FLOW_SECTOR_DAILY_URL
    body = req.call_args.kwargs["json"]
    assert body["sectorList"] == ["1000001065"]
    assert body["fieldList"] == ["sectorMainNetInflow"]
    assert "1000001065" in str(text)


def test_fund_flow_rejects_sectors_with_securities():
    _, fund_flow = _load("gangtise-data", "fund_flow")
    _, runtime = _load("gangtise-data", "gts_runtime")
    with pytest.raises(runtime.ValidationError, match="不能同时"):
        fund_flow.fund_flow_data(securities=["贵州茅台"], sectors=["1000001065"])


def test_fund_flow_ambiguous_sector_name_is_soft_message(tmp_path):
    pkg, fund_flow = _load("gangtise-data", "fund_flow")
    cands = [
        {"sectorId": "1000000366", "sectorName": "半导体", "hierarchy": "中信", "matchScore": 1.0},
        {"sectorId": "1000000537", "sectorName": "半导体", "hierarchy": "申万", "matchScore": 1.0},
    ]
    with patch(f"{pkg}.fund_flow.get_authorization_token", return_value="tok"), patch(
        f"{pkg}.fund_flow.get_authorization_headers", return_value={"Authorization": "tok"}
    ), patch(f"{pkg}.fund_flow._search_sectors", return_value=(cands, None)):
        text = fund_flow.fund_flow_data(sectors=["半导体"], output_dir=str(tmp_path))
    assert "匹配到多个板块" in str(text)
    assert "1000000366" in str(text)
    assert "API error" not in str(text)


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
    assert ci._normalize_root_param_value("calendarType", "交易日") == "TD"
    assert ci._normalize_root_param_value("calendarType", "报告期") == "RD"
    assert ci._normalize_root_param_value("calendarType", "wd") == "WD"
    assert ci._calendar_axis_label(None) == "按指标自动"
    assert ci._calendar_axis_label("RD") == "报告期"
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


def test_calendar_publish_window_is_and_with_event_time():
    _, cal = _load("gangtise-file", "investment_calendar")
    start, end = cal._format_time_range("2026-03-01", "2026-03-02")
    payload = cal._build_payload(
        "forum",
        start,
        end,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        publish_start=start,
        publish_end=end,
    )
    assert payload["startTime"] == start
    assert payload["endTime"] == end
    assert payload["publishStartTime"] == start
    assert payload["publishEndTime"] == end
    for kind in ("roadshow", "site_visit", "strategy_meeting"):
        one_side = cal._build_payload(
            kind, None, None, None, None, None, None, None, None, None, None, None, publish_start=start
        )
        assert one_side["publishStartTime"] == start
        assert "publishEndTime" not in one_side
        assert "startTime" not in one_side
    performance = cal._build_payload(
        "performance", None, None, None, None, None, None, None, None, None, None, None,
        start_date="2026-03-01", publish_start=start,
    )
    assert "publishStartTime" not in performance
    assert performance["startDate"] == "2026-03-01"
    row = cal._format_row(
        "forum",
        {"forumId": "1", "title": "春季论坛", "startTime": start, "endTime": end, "publishTime": start},
    )
    assert row["收录时间"] == "2026-03-01 00:00:00"
    assert row["文件时间"]
    _, runtime = _load("gangtise-file", "gts_runtime")
    with pytest.raises(runtime.ValidationError, match="财报日历"):
        cal.calendar_finder(kind="performance", publish_start_date="2026-03-01")


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
