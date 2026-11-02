"""Ported from gangtise-openapi-cli tests/unit/errors.test.ts."""
import json

import pytest

from gangtise_core.envelope import unwrap
from gangtise_core.errors import ApiError, GangtiseError, ValidationError
from gangtise_core.format import render_mcp_text
from gangtise_core.hints import ERROR_HINTS, distinct_failure_shapes, hint_for
from gangtise_core.result import Result


def test_stores_code_http_and_body():
    err = ApiError("boom", code="999001", http=401, body={"x": 1})
    assert (err.code, err.http, err.body) == ("999001", 401, {"x": 1})


def test_provides_hint_for_known_codes():
    assert ApiError("积分不足", code="999005").hint == ERROR_HINTS["999005"]


@pytest.mark.parametrize("code", ["0000001007", "0000001008", "900002", "8000014", "410110", "410111"])
def test_keeps_hints_for_legacy_codes(code):
    assert ApiError("x", code=code).hint


def test_900002_is_the_wrong_http_method_not_a_missing_uid():
    assert "GET 还是 POST" in ApiError("请求类型有误", code="900002").hint


def test_999006_scopes_retries():
    hint = ApiError("限流", code="999006").hint
    assert "429" in hint and "5xx" in hint


def test_110003_does_not_say_shorten_the_window():
    hint = ApiError("超出权限", code="110003").hint
    assert "缩短窗口无用" in hint


def test_matches_numeric_codes_once_normalized_to_strings():
    with pytest.raises(ApiError) as ei:
        unwrap({"code": 999005, "msg": "积分不足", "status": False})
    assert ei.value.hint == ERROR_HINTS["999005"]


def test_no_hint_for_unknown_or_missing_code():
    assert ApiError("x", code="123456").hint is None
    assert ApiError("x").hint is None


def test_explicit_hint_overrides_table():
    assert ApiError("x", code="999999", hint="检查参数").hint == "检查参数"


def test_hints_carry_the_action_not_a_restatement():
    for code, hint in ERROR_HINTS.items():
        assert hint.strip(), code
        assert len(hint) > 4, code


# ── message hints (EDE 100001 / 100003) ──

def test_reportdate_hint_on_100003():
    err = ApiError("指标 is_op_rev 缺少必填参数 reportDate", code="100003")
    assert "reportDate（报告期）" in err.hint


def test_reportdate_hint_also_under_100001():
    err = ApiError("指标 div_cash_yld 缺少必填参数 reportDate", code="100001")
    assert "reportDate（报告期）" in err.hint


def test_does_not_assert_reportdate_when_only_tradedate_refused():
    err = ApiError("指标 scr_exchg_mkt 不支持参数 tradeDate", code="100003")
    assert "没说该换成哪个" in err.hint
    assert "reportDate（报告期）" not in err.hint


def test_concatenated_message_keeps_the_assertive_reportdate_hint():
    err = ApiError("指标 is_op_rev 不支持参数 tradeDate; 指标 is_op_rev 缺少必填参数 reportDate", code="100003")
    assert "reportDate（报告期）" in err.hint


def test_swap_when_server_names_both_halves_the_other_way_round():
    err = ApiError("指标 qte_close 不支持参数 reportDate; 指标 qte_close 缺少必填参数 tradeDate", code="100003")
    assert "已经点名了两边" in err.hint


def test_both_dates_required_second_wall():
    err = ApiError("指标 div_cash_yld 缺少必填参数 tradeDate", code="100001")
    assert "tradeDate 这次没有下发" in err.hint


def test_batch_with_different_failure_shapes_gets_triage():
    msg = (
        "指标 qte_close 不支持参数 reportDate; 指标 qte_close 缺少必填参数 tradeDate; "
        "指标 pty_cn_name 不支持参数 tradeDate"
    )
    assert distinct_failure_shapes(msg) == 2
    assert "失败的方式不同" in ApiError(msg, code="100003").hint


def test_batch_failing_the_same_way_keeps_the_specific_hint():
    msg = (
        "指标 is_op_rev 不支持参数 tradeDate; 指标 is_op_rev 缺少必填参数 reportDate; "
        "指标 is_dnrpnp 不支持参数 tradeDate; 指标 is_dnrpnp 缺少必填参数 reportDate"
    )
    assert distinct_failure_shapes(msg) == 1
    assert "reportDate（报告期）" in ApiError(msg, code="100003").hint


def test_same_indicator_named_twice_is_still_singular():
    msg = "指标 is_op_rev 缺少必填参数 reportDate; 指标 is_op_rev 缺少必填参数 reportDate"
    assert "reportDate（报告期）" in ApiError(msg, code="100003").hint


def test_other_100003_causes_get_the_generic_code_hint():
    assert hint_for("100003", "请求体字段类型不匹配: size 期望类型 Integer") == ERROR_HINTS["100003"]


# ── traceId / rendering ──

def test_trace_id_from_envelope_and_attached_fallback():
    with pytest.raises(ApiError) as ei:
        unwrap({"code": "999999", "msg": "系统错误", "status": False, "traceId": 12345})
    assert ei.value.trace_id == "12345"
    assert ApiError("x", body={"_traceId": "outer"}).trace_id == "outer"
    assert ApiError("x", trace_id="own", body={"traceId": "other"}).trace_id == "own"


def test_cli_line_matches_ts_format():
    err = ApiError("积分不足", code="999005", trace_id="t-1")
    assert str(err) == f"API error (999005) [trace t-1]: 积分不足 {ERROR_HINTS['999005']}"


def test_http_error_without_envelope_names_the_status():
    with pytest.raises(ApiError) as ei:
        unwrap("<html>bad gateway</html>", http=502)
    assert "HTTP 502" in str(ei.value)
    assert ei.value.exit_code == 1


def test_success_false_envelope_is_an_error():
    with pytest.raises(ApiError):
        unwrap({"success": False, "msg": "nope"})
    assert unwrap({"success": True, "data": {"a": 1}}) == {"a": 1}


def test_mcp_payload_carries_raw_message_hint_and_trace():
    err = ApiError("积分不足", code="999005", trace_id="t-1", http=200)
    payload = json.loads(render_mcp_text(Result.from_error(err)))
    assert payload == {
        "code": "999005",
        "message": "积分不足",
        "http": 200,
        "hint": ERROR_HINTS["999005"],
        "traceId": "t-1",
    }


def test_validation_error_is_a_param_failure():
    err = ValidationError("Invalid --limit: expected an integer")
    assert isinstance(err, GangtiseError)
    assert err.exit_code == 2
    assert str(err) == "Invalid --limit: expected an integer"


@pytest.mark.parametrize("code", ["100001", "100003", "100006", "110002", "120001"])
def test_param_codes_exit_2(code):
    assert ApiError("x", code=code).exit_code == 2


@pytest.mark.parametrize("code,http", [("999005", 200), ("999999", 500), ("", 401), ("999006", 429)])
def test_non_param_failures_exit_1(code, http):
    assert ApiError("x", code=code, http=http).exit_code == 1
