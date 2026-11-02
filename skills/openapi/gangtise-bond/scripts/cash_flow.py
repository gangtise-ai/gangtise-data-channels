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
    BOND_CASH_FLOW_URL,
    add_common_args,
    build_headers,
    describe_period,
    describe_securities,
    error_response,
    normalize_securities_arg,
    plan_lifetime_payloads,
    resolve_field_list,
    run_table_query,
    sort_by_codes,
)

METHOD_NAME = "cash_flow"
DEFAULT_KEYS = ["securityCode", "paymentDate"]

FIELD_CN = {
    "securityCode": "债券代码",
    "paymentDate": "兑付日期",
    "securityName": "债券简称",
    "cashFlowType": "现金流类型",
    "interestPer100": "百元应付利息(元)",
    "principalPer100": "百元应付本金(元)",
    "couponRate": "当期票面利率(%)",
    "taxFree": "利息是否免税",
    "payableCashFlow": "应付现金流(亿元)",
    "remainingBalance": "兑付余额(亿元)",
}


def bond_cash_flow(
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

    # 不传日期时接口只返回已发生的兑付，因此始终按债券存续期显式传区间，以取到完整兑付计划
    payloads = plan_lifetime_payloads(codes, start_date, end_date, {"fieldList": fields}, headers)
    period = describe_period(start_date, end_date)
    return run_table_query(
        url=BOND_CASH_FLOW_URL,
        method_name=METHOD_NAME,
        module_name="bond_cash_flow",
        title=f"{describe_securities(codes, abbrs)}{period} 付息兑付明细",
        payloads=payloads,
        field_cn=FIELD_CN,
        headers=headers,
        output_dir=output_dir,
        notes=notes,
        post_process=lambda df: sort_by_codes(df, codes, "paymentDate"),
    )


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="债券付息兑付明细（open-fundamental / bond/cash-flow）",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--securities",
        required=True,
        help="债券代码/简称/拼音，逗号分隔；亦可传 .csv 路径（含 security_code / 债券代码 等列）",
    )
    parser.add_argument("-sd", "--start-date", default=None, help="兑付日期起始 yyyy-MM-dd；不传返回全部兑付计划")
    parser.add_argument("-ed", "--end-date", default=None, help="兑付日期截止 yyyy-MM-dd；不传返回全部兑付计划")
    add_common_args(parser, "字段英文名或中文名，逗号分隔；不传返回全部 10 个字段")
    args = parser.parse_args()

    try:
        securities = normalize_securities_arg(args.securities)
    except Exception as e:
        print(f"解析 --securities 失败: {e}")
        sys.exit(1)
    if not securities:
        parser.error("请指定 --securities")

    print(
        bond_cash_flow(
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
