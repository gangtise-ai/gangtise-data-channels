# GENERATED FILE. Do not edit. Source: skills/openapi/gangtise-bond/scripts/rating.py
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

from .security import resolve_or_error
from .utils import (
    BOND_RATING_OVERVIEW_URL,
    add_common_args,
    build_headers,
    chunked,
    describe_securities,
    error_response,
    normalize_securities_arg,
    resolve_field_list,
    run_table_query,
)

METHOD_NAME = "rating"
MAX_SECURITIES_PER_REQUEST = 10
DEFAULT_KEYS = ["securityCode"]

FIELD_CN = {
    # 基础标识
    "securityCode": "债券代码",
    "securityName": "债券简称",
    # 债项评级
    "bondRating": "债项评级",
    "bondRatingDate": "债项评级日期",
    "bondRatingAgency": "债项评级机构",
    "bondRatingType": "债项评级类别",
    "bondRatingOutlook": "债项评级展望",
    # 发行人评级
    "issuerName": "发行人",
    "issuerRating": "主体评级",
    "issuerRatingDate": "主体评级日期",
    "issuerRatingAgency": "主体评级机构",
    "issuerRatingType": "主体评级类别",
    "issuerRatingOutlook": "主体评级展望",
    # 担保人评级
    "guarantorName": "担保人",
    "guarantorRating": "担保人评级",
    "guarantorRatingDate": "担保人评级日期",
    "guarantorRatingAgency": "担保人评级机构",
    "guarantorRatingType": "担保人评级类别",
    "guarantorRatingOutlook": "担保人评级展望",
}


def bond_rating_overview(
    securities: List[str],
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

    payloads = [{"securityList": chunk, "fieldList": fields} for chunk in chunked(codes, MAX_SECURITIES_PER_REQUEST)]
    return run_table_query(
        url=BOND_RATING_OVERVIEW_URL,
        method_name=METHOD_NAME,
        module_name="bond_rating_overview",
        title=f"{describe_securities(codes, abbrs)}评级一览",
        payloads=payloads,
        field_cn=FIELD_CN,
        headers=headers,
        output_dir=output_dir,
        notes=notes,
    )


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="债券评级一览：债项 / 发行人 / 担保人最新评级（open-fundamental / bond/rating-overview）",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--securities",
        required=True,
        help="债券代码/简称/拼音，逗号分隔；亦可传 .csv 路径。接口单次上限 10 只，超出自动分批",
    )
    add_common_args(parser, "字段英文名或中文名，逗号分隔；不传返回全部 19 个字段")
    args = parser.parse_args()

    try:
        securities = normalize_securities_arg(args.securities)
    except Exception as e:
        print(f"解析 --securities 失败: {e}")
        sys.exit(1)
    if not securities:
        parser.error("请指定 --securities")

    print(bond_rating_overview(securities, field_list=args.field_list, output_dir=args.output_dir or None))


if __name__ == "__main__":
    sys.stdout = TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="ignore")
    main()
