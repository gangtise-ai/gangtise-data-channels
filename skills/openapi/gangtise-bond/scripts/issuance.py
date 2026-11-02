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
    BOND_ISSUANCE_DETAIL_URL,
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

METHOD_NAME = "issuance"
DEFAULT_KEYS = ["securityCode", "issueBatchNo"]

FIELD_CN = {
    # 基础标识
    "securityCode": "债券代码",
    "issueBatchNo": "发行批次",
    "securityName": "债券简称",
    # 发行时点
    "issueAnnouncementDate": "发行公告日",
    "biddingDate": "发行招标日",
    "paymentDate": "发行缴款日",
    # 发行方式
    "underwritingMethod": "承销方式",
    "biddingMethod": "招标方式",
    "biddingTarget": "招标标的",
    # 发行结果
    "plannedIssueSize": "计划发行总额(亿元)",
    "actualIssueSize": "实际发行总额(亿元)",
    "issuePrice": "发行价格(元)",
    "referenceYield": "参考收益率(%)",
    "marginalRate": "边际利率(%)",
    "bidToCoverRatio": "全场认购倍数",
    "marginalBidToCoverRatio": "边际认购倍数",
}


def bond_issuance_detail(
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

    if start_date or end_date:
        payloads = plan_lifetime_payloads(codes, start_date, end_date, {"fieldList": fields}, headers)
    else:
        payloads = [{"securityList": codes, "fieldList": fields}]
    period = describe_period(start_date, end_date)
    return run_table_query(
        url=BOND_ISSUANCE_DETAIL_URL,
        method_name=METHOD_NAME,
        module_name="bond_issuance_detail",
        title=f"{describe_securities(codes, abbrs)}{period} 发行增发明细",
        payloads=payloads,
        field_cn=FIELD_CN,
        headers=headers,
        output_dir=output_dir,
        notes=notes,
        post_process=lambda df: sort_by_codes(df, codes, "issueBatchNo"),
    )


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="债券发行增发明细（open-fundamental / bond/issuance-detail）",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--securities",
        required=True,
        help="债券代码/简称/拼音，逗号分隔；亦可传 .csv 路径（含 security_code / 债券代码 等列）",
    )
    parser.add_argument("-sd", "--start-date", default=None, help="发行公告日起始 yyyy-MM-dd；不传返回全部记录")
    parser.add_argument("-ed", "--end-date", default=None, help="发行公告日截止 yyyy-MM-dd；不传返回全部记录")
    add_common_args(parser, "字段英文名或中文名，逗号分隔；不传返回全部 16 个字段")
    args = parser.parse_args()

    try:
        securities = normalize_securities_arg(args.securities)
    except Exception as e:
        print(f"解析 --securities 失败: {e}")
        sys.exit(1)
    if not securities:
        parser.error("请指定 --securities")

    print(
        bond_issuance_detail(
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
