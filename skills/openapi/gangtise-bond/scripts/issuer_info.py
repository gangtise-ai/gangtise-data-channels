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

import pandas as pd

from .security import resolve_issuers_or_error, resolve_or_error
from .utils import (
    BOND_ISSUER_INFO_URL,
    add_common_args,
    build_headers,
    chunked,
    describe_securities,
    error_response,
    normalize_securities_arg,
    parse_str_list,
    resolve_field_list,
    run_table_query,
)

METHOD_NAME = "issuer_info"
MAX_KEYS_PER_REQUEST = 10000
DEFAULT_KEYS = ["issuerName"]
QUERY_CODE_COLUMN = "queryBondCode"

FIELD_CN = {
    # 主体标识
    "issuerName": "发行人",
    "unifiedSocialCreditCode": "统一社会信用代码",
    "enterpriseNature": "企业性质",
    "listedCompany": "是否上市公司",
    # 行业归属
    "nationalIndustry": "国民经济行业",
    "swIndustry": "申万行业",
    # 工商信息
    "establishmentDate": "设立日期",
    "registeredCapital": "注册资本(万元)",
    "registeredAddress": "注册地址",
    "provinceCity": "所属省市",
    "legalRepresentative": "法人代表",
    "generalManager": "总经理",
    # 经营与联系方式
    "companyProfile": "公司简介",
    "businessScope": "经营范围",
    "website": "公司网址",
    "telephone": "联系电话",
    "email": "电子邮箱",
    # 评级
    "latestIssuerRating": "最新主体评级",
    "ratingAgency": "评级机构",
    # 存续债券
    "outstandingBondList": "存续债券",
}

DEFAULT_FIELDS = [
    "unifiedSocialCreditCode",
    "enterpriseNature",
    "listedCompany",
    "swIndustry",
    "provinceCity",
    "establishmentDate",
    "registeredCapital",
    "latestIssuerRating",
    "ratingAgency",
    "outstandingBondList",
]


def bond_issuer_info(
    securities: Optional[List[str]] = None,
    issuers: Optional[List[str]] = None,
    field_list: Optional[List[str]] = None,
    output_dir: Optional[str] = None,
) -> str:
    headers = build_headers()
    if not headers:
        return error_response(METHOD_NAME, "未配置 gangtise 授权，无法调用 open 接口", output_dir)
    if bool(securities) == bool(issuers):
        return error_response(METHOD_NAME, "--securities 与 --issuers 必须且只能传入其中一个", output_dir)
    fields, err = resolve_field_list(field_list, FIELD_CN, DEFAULT_KEYS, DEFAULT_FIELDS)
    if err:
        return error_response(METHOD_NAME, err, output_dir)

    notes: List[str] = []
    post_process = None
    if securities:
        codes, abbrs, notes, err_out = resolve_or_error(securities, headers, METHOD_NAME, output_dir)
        if err_out:
            return err_out
        payloads = [{"securityList": chunk, "fieldList": fields} for chunk in chunked(codes, MAX_KEYS_PER_REQUEST)]
        title = f"{describe_securities(codes, abbrs)}的发债主体信息"

        def post_process(df: pd.DataFrame) -> pd.DataFrame:
            # 按债券查询时为单行型：行数、行序与去重后的 securityList 一致
            if len(df) != len(codes):
                return df
            out = df.copy()
            out.insert(0, QUERY_CODE_COLUMN, codes)
            return out
    else:
        names, resolve_notes, err_out = resolve_issuers_or_error(issuers, headers, METHOD_NAME, output_dir)
        if err_out:
            return err_out
        notes.extend(resolve_notes or [])
        payloads = [{"issuerNameList": chunk, "fieldList": fields} for chunk in chunked(names, MAX_KEYS_PER_REQUEST)]
        title = f"{names[0]}等{len(names)}个发债主体信息" if len(names) > 1 else f"{names[0]}发债主体信息"
        notes.append("已解析为发行人全称后查询")

    return run_table_query(
        url=BOND_ISSUER_INFO_URL,
        method_name=METHOD_NAME,
        module_name="bond_issuer_info",
        title=title,
        payloads=payloads,
        field_cn={QUERY_CODE_COLUMN: "查询债券代码", **FIELD_CN},
        headers=headers,
        output_dir=output_dir,
        notes=notes,
        post_process=post_process,
    )


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="发债主体基本信息（open-fundamental / bond/issuer-info）",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--securities",
        default=None,
        help="债券代码/简称/拼音，逗号分隔；亦可传 .csv 路径。返回这些债券对应的发行人",
    )
    group.add_argument("--issuers", default=None, help="发债主体全称或简称，逗号分隔。简称多家匹配时全部列出，不自动取最接近的一家")
    add_common_args(parser, "字段英文名或中文名，逗号分隔；不传返回常用字段，传 all 返回全部 20 个字段")
    args = parser.parse_args()

    try:
        securities = normalize_securities_arg(args.securities)
    except Exception as e:
        print(f"解析 --securities 失败: {e}")
        sys.exit(1)

    print(
        bond_issuer_info(
            securities=securities or None,
            issuers=parse_str_list(args.issuers) or None,
            field_list=args.field_list,
            output_dir=args.output_dir or None,
        )
    )


if __name__ == "__main__":
    sys.stdout = TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="ignore")
    main()
