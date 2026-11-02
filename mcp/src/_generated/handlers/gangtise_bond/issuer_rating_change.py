# GENERATED FILE. Do not edit. Source: skills/openapi/gangtise-bond/scripts/issuer_rating_change.py
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

from .security import resolve_issuers_or_error, resolve_or_error
from .utils import (
    BOND_ISSUER_RATING_CHANGE_URL,
    add_common_args,
    apply_optional_date_range,
    build_headers,
    chunked,
    describe_period,
    describe_securities,
    error_response,
    normalize_securities_arg,
    parse_str_list,
    resolve_field_list,
    run_table_query,
)

METHOD_NAME = "issuer_rating_change"
# 接口单次最多命中 10 个发行人；每只债券 / 每个名称至多对应 1 个发行人，按 10 个一批可保证不超限
MAX_KEYS_PER_REQUEST = 10
DEFAULT_KEYS = ["issuerName", "announcementDate"]

FIELD_CN = {
    # 主体标识
    "issuerName": "发行人",
    "announcementDate": "公告日期",
    "enterpriseNature": "企业性质",
    "region": "所属地域",
    # 变动记录
    "ratingType": "评级类型",
    "currentRating": "本次评级",
    "previousRating": "上次评级",
    "changeDirection": "变动方向",
    "ratingOutlook": "评级展望",
    "latestRatingDate": "最新评级日期",
    "previousRatingDate": "上次评级日期",
    "ratingAgency": "评级机构",
}


def bond_issuer_rating_change(
    securities: Optional[List[str]] = None,
    issuers: Optional[List[str]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    field_list: Optional[List[str]] = None,
    output_dir: Optional[str] = None,
) -> str:
    headers = build_headers()
    if not headers:
        return error_response(METHOD_NAME, "未配置 gangtise 授权，无法调用 open 接口", output_dir)
    if bool(securities) == bool(issuers):
        return error_response(METHOD_NAME, "--securities 与 --issuers 必须且只能传入其中一个", output_dir)
    fields, err = resolve_field_list(field_list, FIELD_CN, DEFAULT_KEYS)
    if err:
        return error_response(METHOD_NAME, err, output_dir)

    notes: List[str] = []
    if securities:
        codes, abbrs, notes, err_out = resolve_or_error(securities, headers, METHOD_NAME, output_dir)
        if err_out:
            return err_out
        key, keys = "securityList", codes
        subject = f"{describe_securities(codes, abbrs)}的发债主体"
    else:
        keys, resolve_notes, err_out = resolve_issuers_or_error(issuers, headers, METHOD_NAME, output_dir)
        if err_out:
            return err_out
        notes.extend(resolve_notes or [])
        key = "issuerNameList"
        subject = f"{keys[0]}等{len(keys)}个发债主体" if len(keys) > 1 else keys[0]
        notes.append("已解析为发行人全称后查询")

    payloads = []
    for chunk in chunked(keys, MAX_KEYS_PER_REQUEST):
        payloads.append(apply_optional_date_range({key: chunk, "fieldList": fields}, start_date, end_date))
    period = describe_period(start_date, end_date)
    return run_table_query(
        url=BOND_ISSUER_RATING_CHANGE_URL,
        method_name=METHOD_NAME,
        module_name="bond_issuer_rating_change",
        title=f"{subject}{period} 评级变动记录",
        payloads=payloads,
        field_cn=FIELD_CN,
        headers=headers,
        output_dir=output_dir,
        notes=notes,
        post_process=lambda df: df.drop_duplicates().reset_index(drop=True),
    )


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="发债主体评级变动（open-fundamental / bond/issuer-rating-change）",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--securities",
        default=None,
        help="债券代码/简称/拼音，逗号分隔；亦可传 .csv 路径。返回这些债券对应发行人的评级变动",
    )
    group.add_argument("--issuers", default=None, help="发债主体全称或简称，逗号分隔。简称多家匹配时全部列出，不自动取最接近的一家")
    parser.add_argument("-sd", "--start-date", default=None, help="公告日期起始 yyyy-MM-dd；不传返回全部历史")
    parser.add_argument("-ed", "--end-date", default=None, help="公告日期截止 yyyy-MM-dd；不传返回全部历史")
    add_common_args(parser, "字段英文名或中文名，逗号分隔；不传返回全部 12 个字段")
    args = parser.parse_args()

    try:
        securities = normalize_securities_arg(args.securities)
    except Exception as e:
        print(f"解析 --securities 失败: {e}")
        sys.exit(1)

    print(
        bond_issuer_rating_change(
            securities=securities or None,
            issuers=parse_str_list(args.issuers) or None,
            start_date=args.start_date,
            end_date=args.end_date,
            field_list=args.field_list,
            output_dir=args.output_dir or None,
        )
    )


if __name__ == "__main__":
    sys.stdout = TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="ignore")
    main()
