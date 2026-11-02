# GENERATED FILE. Do not edit. Source: skills/openapi/gangtise-bond/scripts/issuance_plan.py
# Regenerate: python3 scripts/generate.py
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

from .utils import (
    BOND_ISSUANCE_PLAN_URL,
    add_common_args,
    build_headers,
    default_date_range,
    error_response,
    resolve_field_list,
    run_table_query,
)

METHOD_NAME = "issuance_plan"
DEFAULT_KEYS = ["issueDate"]

FIELD_CN = {
    # 计划标识
    "issueDate": "计划发行日期",
    "year": "年度",
    "issuer": "发行人",
    # 债券要素
    "bondType": "债券类型",
    "term": "期限(年)",
    "issueSize": "计划发行量(亿元)",
    "interestRateType": "利率类型",
    "interestFrequency": "付息频率",
    "crossMarket": "是否跨市场",
}


def bond_issuance_plan(
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

    start, end = default_date_range(start_date, end_date, back_days=0, forward_days=30)
    payload = {"startDate": start, "endDate": end, "fieldList": fields}
    return run_table_query(
        url=BOND_ISSUANCE_PLAN_URL,
        method_name=METHOD_NAME,
        module_name="bond_issuance_plan",
        title=f"{start}~{end} 利率债发行计划",
        payloads=[payload],
        field_cn=FIELD_CN,
        headers=headers,
        output_dir=output_dir,
    )


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="利率债发行计划（open-fundamental / bond/issuance-plan）",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-sd", "--start-date", default=None, help="发行日期起始 yyyy-MM-dd；不传默认今天")
    parser.add_argument("-ed", "--end-date", default=None, help="发行日期截止 yyyy-MM-dd；不传默认今天起 30 天")
    add_common_args(parser, "字段英文名或中文名，逗号分隔；不传返回全部 9 个字段")
    args = parser.parse_args()

    print(
        bond_issuance_plan(
            start_date=args.start_date,
            end_date=args.end_date,
            field_list=args.field_list,
            output_dir=args.output_dir or None,
        )
    )


if __name__ == "__main__":
    sys.stdout = TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="ignore")
    main()
