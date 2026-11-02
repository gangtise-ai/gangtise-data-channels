import json

from gangtise_core.envelope import unwrap
from gangtise_core.errors import ApiError, PartialResultError
from gangtise_core.format import emit_cli, render_cli
from gangtise_core.present import failure_result
from gangtise_core.result import Result
from gangtise_core.ziprow import zip_field_row
import pytest


def test_unwrap_points_insufficient():
    with pytest.raises(ApiError) as ei:
        unwrap({"code": "999005", "msg": "积分不足", "status": False, "traceId": "t-1"})
    assert ei.value.code == "999005"
    assert ei.value.trace_id == "t-1"
    assert ei.value.exit_code == 1


def test_unwrap_http_business_code_200():
    data = unwrap({"code": 200, "status": True, "data": {"list": [1]}})
    assert data == {"list": [1]}


def test_unwrap_param_error_exit_2():
    with pytest.raises(ApiError) as ei:
        unwrap({"code": "100003", "msg": "参数错误", "status": False})
    assert ei.value.exit_code == 2


def test_unwrap_inner_ede_envelope():
    with pytest.raises(ApiError) as ei:
        unwrap(
            {
                "code": "000000",
                "status": True,
                "traceId": "outer",
                "data": {"code": "130001", "msg": "无权限", "status": False},
            }
        )
    assert ei.value.code == "130001"
    assert ei.value.trace_id == "outer"


def test_emit_cli_maps_exit_codes(capsys):
    err = ApiError("积分不足", code="999005", trace_id="t-1")
    assert emit_cli(Result.from_error(err)) == 1
    captured = capsys.readouterr()
    assert "999005" in captured.err
    assert captured.out == ""


def test_vacuum_is_success_exit_0():
    result = failure_result({"state": "error", "message": "未找到行情数据"})
    assert result.ok
    assert result.exit_code == 0
    assert emit_cli(result) == 0


def test_zip_field_row_rejects_mismatch():
    from gangtise_core.errors import StructuralError

    with pytest.raises(StructuralError):
        zip_field_row(["a", "b"], [1])


def test_format_json_emits_data_not_markdown():
    result = Result.success(text="### 行情\n忽略", data=[{"证券代码": "600519.SH", "收盘价": 1.2}])
    payload = json.loads(render_cli(result, "json"))
    assert payload == [{"证券代码": "600519.SH", "收盘价": 1.2}]


def test_rate_limit_exit_1():
    with pytest.raises(ApiError) as ei:
        unwrap({"code": "999006", "msg": "限流", "status": False})
    assert ei.value.exit_code == 1


def test_partial_fail_list_exit_3(capsys):
    err = PartialResultError("部分失败", code="000000", trace_id="t-p")
    assert emit_cli(Result.from_error(err)) == 3
    assert "部分失败" in capsys.readouterr().err


def test_verbose_prints_compensated_ids(capsys):
    result = Result.success(text="ok", data=[], tool="company_indicator")
    assert emit_cli(result, verbose=True) == 0
    err = capsys.readouterr().err
    assert "compensated: C-001" in err
    assert "compensated: C-002" in err
    assert "compensated: C-003" in err
