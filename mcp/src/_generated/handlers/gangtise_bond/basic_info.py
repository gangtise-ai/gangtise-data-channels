# GENERATED FILE. Do not edit. Source: skills/openapi/gangtise-bond/scripts/basic_info.py
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
    BOND_BASIC_INFO_URL,
    add_common_args,
    build_headers,
    chunked,
    describe_securities,
    error_response,
    normalize_securities_arg,
    resolve_field_list,
    run_table_query,
)

METHOD_NAME = "basic_info"
MAX_SECURITIES_PER_REQUEST = 10000
DEFAULT_KEYS = ["securityCode"]

FIELD_CN = {
    # 基础标识
    "securityCode": "债券代码",
    "securityName": "债券简称",
    "securityFullName": "债券全称",
    "bondType": "债券类型",
    "exchange": "交易市场",
    "currency": "发行币种",
    # 发行信息
    "issuer": "发行人",
    "issueMethod": "发行方式",
    "leadUnderwriter": "主承销商",
    "issueSize": "发行总量(亿元)",
    "outstandingBalance": "当前余额(亿元)",
    "parValue": "初始面值/最新面值(元)",
    "latestParValue": "最新面值(元/张)",
    "issuePriceOrReferenceYield": "发行价格(元)/参考收益率(%)",
    "issueFee": "发行手续费(元)",
    "biddingTarget": "招标标的",
    "accountingType": "会计处理类型",
    "issuerRegion": "发行人所属地区",
    "industry": "所属行业",
    # 期限与日期
    "issueAnnouncementDate": "发行公告日",
    "issueDate": "发行日期",
    "issueResultAnnouncementDate": "发行结果公告日",
    "listDate": "上市日期",
    "delistDate": "摘牌日期",
    "valueDate": "起息日期",
    "maturityDate": "到期日期",
    "actualMaturityDate": "实际到期日",
    "issueTerm": "发行期限(年)",
    "remainingTerm": "剩余期限(年)",
    "remainingDays": "剩余天数",
    # 利率与付息
    "couponRate": "票面利率(%)",
    "interestRateType": "利率类型",
    "interestFrequency": "付息频率",
    "interestRateDescription": "利率说明",
    "interestAccrualMethod": "计息方式",
    "nextInterestPaymentDate": "下一付息日",
    "daysToNextInterestPayment": "距下一付息日(天)",
    "compensationInterest": "补偿利息(元/张)",
    "compensationRate": "补偿利率(%)",
    # 评级
    "latestBondRating": "最新债项评级",
    "latestRating": "最新评级(主体/债项)",
    "issueRating": "发行时评级(主体/债项)",
    "ratingAgency": "评级机构",
    # 担保
    "guarantor": "担保人",
    "guaranteeMethod": "担保方式",
    "guaranteePeriod": "担保时段",
    # 特殊条款
    "specialTerms": "内含特殊条款",
    "termsDescription": "条款说明",
    "nextExerciseDate": "下一行权日",
    "putDate": "债券回售日",
    "conditionalPutStartDate": "条件回售起始日期",
    "conditionalPutEndDate": "条件回售截止日期",
    "specialRevisionStartDate": "特别修正起始日期",
    "specialRevisionEndDate": "特别修正截止日期",
    # 质押回购
    "pledgeCode": "质押券代码",
    "standardBondConversion": "折合标准券(元)",
    # ABS 专项
    "absProjectName": "ABS项目名称",
    "absUnderlyingAssetType": "ABS基础资产类型",
    "trusteeOrPlanManager": "受托机构/计划管理人",
    "originator": "发起机构/原始权益人",
    # 可转债专项
    "conversionStartDate": "转换期起始日",
    "conversionEndDate": "转换期截止日",
    "conversionSecurityCode": "转股证券代码",
    "conversionDeclarationCode": "转股申报代码",
    "lastConversionDate": "最后转股日",
}

DEFAULT_FIELDS = [
    "securityName",
    "securityFullName",
    "bondType",
    "exchange",
    "issuer",
    "issueSize",
    "outstandingBalance",
    "couponRate",
    "interestRateType",
    "valueDate",
    "maturityDate",
    "remainingTerm",
    "latestRating",
    "specialTerms",
    "nextExerciseDate",
]


def bond_basic_info(
    securities: List[str],
    field_list: Optional[List[str]] = None,
    output_dir: Optional[str] = None,
) -> str:
    headers = build_headers()
    if not headers:
        return error_response(METHOD_NAME, "未配置 gangtise 授权，无法调用 open 接口", output_dir)
    fields, err = resolve_field_list(field_list, FIELD_CN, DEFAULT_KEYS, DEFAULT_FIELDS)
    if err:
        return error_response(METHOD_NAME, err, output_dir)
    codes, abbrs, notes, err_out = resolve_or_error(securities, headers, METHOD_NAME, output_dir)
    if err_out:
        return err_out

    payloads = [{"securityList": chunk, "fieldList": fields} for chunk in chunked(codes, MAX_SECURITIES_PER_REQUEST)]
    return run_table_query(
        url=BOND_BASIC_INFO_URL,
        method_name=METHOD_NAME,
        module_name="bond_basic_info",
        title=f"{describe_securities(codes, abbrs)}基本资料",
        payloads=payloads,
        field_cn=FIELD_CN,
        headers=headers,
        output_dir=output_dir,
        notes=notes,
    )


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="债券基本资料（open-fundamental / bond/basic-info）",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--securities",
        required=True,
        help="债券代码/简称/拼音，逗号分隔；亦可传 .csv 路径（含 security_code / 债券代码 等列）",
    )
    add_common_args(parser, "字段英文名或中文名，逗号分隔；不传返回常用字段，传 all 返回全部 65 个字段")
    args = parser.parse_args()

    try:
        securities = normalize_securities_arg(args.securities)
    except Exception as e:
        print(f"解析 --securities 失败: {e}")
        sys.exit(1)
    if not securities:
        parser.error("请指定 --securities")

    print(bond_basic_info(securities, field_list=args.field_list, output_dir=args.output_dir or None))


if __name__ == "__main__":
    sys.stdout = TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="ignore")
    main()
