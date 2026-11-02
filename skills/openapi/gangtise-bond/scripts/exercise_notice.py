if __name__ == "__main__" and not __package__:
    import importlib.util
    from pathlib import Path as _P
    _launch = _P(__file__).resolve().parent / "_launch.py"
    _spec = importlib.util.spec_from_file_location("_gts_skill_launch", _launch)
    _mod = importlib.util.module_from_spec(_spec)
    assert _spec and _spec.loader
    _spec.loader.exec_module(_mod)
    raise SystemExit(_mod.relaunch(__file__))

import os
import sys
from io import TextIOWrapper
from typing import List, Optional

from .security import resolve_or_error
from .utils import (
    BOND_EXERCISE_NOTICE_URL,
    add_common_args,
    apply_optional_date_range,
    build_headers,
    describe_period,
    describe_securities,
    error_response,
    normalize_securities_arg,
    resolve_field_list,
    run_table_query,
)

METHOD_NAME = "exercise_notice"
DEFAULT_KEYS = ["securityCode", "exerciseDate"]

FIELD_CN = {
    # 基础标识
    "securityCode": "债券代码",
    "exerciseDate": "行权日",
    "securityName": "债券简称",
    # 行权安排
    "optionType": "权利类型",
    "exerciseApplyStartDate": "行权申请起始日",
    "exerciseApplyEndDate": "行权申请截止日",
    "exerciseAnnouncementDate": "行权公告日",
    "exerciseSettlementDate": "行权资金到账日",
    # 行权结果
    "exercisePrice": "行权价格(元)",
    "exerciseAmount": "行权金额(亿元)",
    "balanceAfterExercise": "行权后余额(亿元)",
}


def bond_exercise_notice(
    securities: List[str],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    field_list: Optional[List[str]] = None,
    output_dir: Optional[str] = None,
) -> str:
    headers = build_headers()
    if not headers:
        return error_response(METHOD_NAME, "未配置 gangtise 授权，无法调用 open 接口", output_dir)
    fields, err = resolve_field_list(field_list, FIELD_CN, DEFAULT_KEYS)
    if err:
        return error_response(METHOD_NAME, err, output_dir)
    codes, abbrs, notes, err_out = resolve_or_error(securities, headers, METHOD_NAME, output_dir)
    if err_out:
        return err_out

    payload = apply_optional_date_range({"securityList": codes, "fieldList": fields}, start_date, end_date)
    period = describe_period(start_date, end_date)
    return run_table_query(
        url=BOND_EXERCISE_NOTICE_URL,
        method_name=METHOD_NAME,
        module_name="bond_exercise_notice",
        title=f"{describe_securities(codes, abbrs)}{period} 行权安排",
        payloads=[payload],
        field_cn=FIELD_CN,
        headers=headers,
        output_dir=output_dir,
        notes=notes,
    )


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="含权债行权提示（open-fundamental / bond/exercise-notice）",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--securities",
        required=True,
        help="债券代码/简称/拼音，逗号分隔；亦可传 .csv 路径（含 security_code / 债券代码 等列）",
    )
    parser.add_argument("-sd", "--start-date", default=None, help="行权日起始 yyyy-MM-dd；不传不限")
    parser.add_argument("-ed", "--end-date", default=None, help="行权日截止 yyyy-MM-dd；不传不限")
    add_common_args(parser, "字段英文名或中文名，逗号分隔；不传返回全部 11 个字段")
    args = parser.parse_args()

    try:
        securities = normalize_securities_arg(args.securities)
    except Exception as e:
        print(f"解析 --securities 失败: {e}")
        sys.exit(1)
    if not securities:
        parser.error("请指定 --securities")

    print(
        bond_exercise_notice(
            securities,
            start_date=args.start_date,
            end_date=args.end_date,
            field_list=args.field_list,
            output_dir=args.output_dir or None,
        )
    )


if __name__ == "__main__":
    sys.stdout = TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="ignore")
    main()
