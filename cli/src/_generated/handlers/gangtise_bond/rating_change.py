# GENERATED FILE. Do not edit. Source: skills/openapi/gangtise-bond/scripts/rating_change.py
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
    BOND_RATING_CHANGE_URL,
    add_common_args,
    apply_optional_date_range,
    build_headers,
    chunked,
    describe_period,
    describe_securities,
    error_response,
    normalize_securities_arg,
    resolve_field_list,
    run_table_query,
)

METHOD_NAME = "rating_change"
MAX_SECURITIES_PER_REQUEST = 10
DEFAULT_KEYS = ["securityCode", "announcementDate"]

FIELD_CN = {
    # 基础标识
    "securityCode": "债券代码",
    "announcementDate": "公告日期",
    "securityName": "债券简称",
    "bondType": "债券类型",
    # 变动记录
    "ratingType": "评级类型",
    "currentRating": "本次评级",
    "previousRating": "上次评级",
    "changeDirection": "变动方向",
    "ratingOutlook": "评级展望",
    "latestRatingDate": "最新评级日期",
    "ratingAgency": "评级机构",
}


def bond_rating_change(
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

    payloads = [
        apply_optional_date_range({"securityList": chunk, "fieldList": fields}, start_date, end_date)
        for chunk in chunked(codes, MAX_SECURITIES_PER_REQUEST)
    ]
    return run_table_query(
        url=BOND_RATING_CHANGE_URL,
        method_name=METHOD_NAME,
        module_name="bond_rating_change",
        title=f"{describe_securities(codes, abbrs)}{describe_period(start_date, end_date)} 债项评级变动",
        payloads=payloads,
        field_cn=FIELD_CN,
        headers=headers,
        output_dir=output_dir,
        notes=notes,
    )


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="债项评级变动：债券历次评级变动记录（open-fundamental / bond/rating-change）",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--securities",
        required=True,
        help="债券代码/简称/拼音，逗号分隔；亦可传 .csv 路径。接口单次上限 10 只，超出自动分批",
    )
    parser.add_argument("-sd", "--start-date", default=None, help="公告日期起始 yyyy-MM-dd；不传返回全部历史")
    parser.add_argument("-ed", "--end-date", default=None, help="公告日期截止 yyyy-MM-dd；不传返回全部历史")
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
        bond_rating_change(
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
