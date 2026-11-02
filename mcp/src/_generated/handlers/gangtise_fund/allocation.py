# GENERATED FILE. Do not edit. Source: skills/openapi/gangtise-fund/scripts/allocation.py
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
    FUND_ASSET_ALLOCATION_URL,
    FUND_BOND_TYPE_ALLOCATION_URL,
    FUND_FUND_TYPE_ALLOCATION_URL,
    FUND_INDUSTRY_ALLOCATION_URL,
    add_date_args,
    add_output_arg,
    error_response,
    normalize_securities_arg,
    parse_choice,
    parse_choices,
    parse_types,
    query_by_codes,
)

METHOD_NAME = "allocation"
TYPE_ORDER = ("asset", "industry", "bond", "fund")
TYPE_ALIAS = {
    "asset": "asset",
    "资产配置": "asset",
    "资产": "asset",
    "industry": "industry",
    "行业": "industry",
    "持股行业": "industry",
    "持股行业分布": "industry",
    "bond": "bond",
    "券种": "bond",
    "持有券种": "bond",
    "持有券种分布": "bond",
    "fund": "fund",
    "基金类型": "fund",
    "持有基金类型": "fund",
    "持有基金类型分布": "fund",
}
LEVEL_ALIAS = {
    "level1": "level1",
    "1": "level1",
    "一级": "level1",
    "level2": "level2",
    "2": "level2",
    "二级": "level2",
}
STANDARD_ALIAS = {
    "swindustry": "swIndustry",
    "sw": "swIndustry",
    "申万": "swIndustry",
    "申万一级": "swIndustry",
    "citicindustry": "citicIndustry",
    "citic": "citicIndustry",
    "中信": "citicIndustry",
    "中信一级": "citicIndustry",
}
POSITION_ALIAS = {
    "top": "top",
    "重仓": "top",
    "重仓股票": "top",
    "all": "all",
    "全部": "all",
    "全部持股": "all",
}

ASSET_FIELD_CN = {
    "fundCode": "基金代码",
    "fundName": "基金简称",
    "reportDate": "报告期",
    "assetLevel": "资产层级",
    "assetType": "资产类型代码",
    "assetTypeName": "资产类型",
    "holdingValue": "金额(元)",
    "pctToTotalAsset": "占基金资产总值比(%)",
}
INDUSTRY_FIELD_CN = {
    "fundCode": "基金代码",
    "fundName": "基金简称",
    "reportDate": "报告期",
    "industryStandard": "行业分类标准",
    "industryCode": "行业代码",
    "industryName": "行业名称",
    "pctToNav": "占基金净值比(%)",
    "positionType": "持仓类型",
}
BOND_FIELD_CN = {
    "fundCode": "基金代码",
    "fundName": "基金简称",
    "reportDate": "报告期",
    "bondTypeCode": "券种代码",
    "bondTypeName": "券种名称",
    "pctToNav": "占基金净值比(%)",
}
FUND_FIELD_CN = {
    "fundCode": "基金代码",
    "fundName": "基金简称",
    "reportDate": "报告期",
    "investTypeCodeLevel1": "一级分类代码",
    "investTypeNameLevel1": "一级分类",
    "pctToNav": "占基金净值比(%)",
    "positionType": "持仓类型",
}


def fund_allocation(
    securities: List[str],
    query_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    asset_level: Optional[List[str]] = None,
    industry_standard: Optional[str] = None,
    position_type: Optional[str] = None,
    output_dir: Optional[str] = None,
):
    types, err = parse_types(query_type, TYPE_ALIAS, TYPE_ORDER, ("asset",))
    if err:
        return error_response(METHOD_NAME, err, output_dir)
    asset_level, err = parse_choices(asset_level, LEVEL_ALIAS, "资产层级")
    if err:
        return error_response(METHOD_NAME, err, output_dir)
    industry_standard, err = parse_choice(industry_standard, STANDARD_ALIAS, "行业分类标准")
    if err:
        return error_response(METHOD_NAME, err, output_dir)
    position_type, err = parse_choice(position_type, POSITION_ALIAS, "持仓类型")
    if err:
        return error_response(METHOD_NAME, err, output_dir)

    notes: List[str] = []
    if asset_level and "asset" not in types:
        notes.append("[WARNING] --asset-level 仅对资产配置生效，本次未使用")
    if industry_standard and "industry" not in types:
        notes.append("[WARNING] --industry-standard 仅对持股行业分布生效，本次未使用")
    if position_type and "industry" not in types:
        notes.append("[WARNING] --position-type 仅对持股行业分布生效，本次未使用")

    jobs = []
    if "asset" in types:
        extra = {"assetLevelList": list(asset_level)} if asset_level else {}
        jobs.append({
            "url": FUND_ASSET_ALLOCATION_URL,
            "module": "asset_allocation",
            "label": "资产配置",
            "field_cn": ASSET_FIELD_CN,
            "extra": extra,
        })
    if "industry" in types:
        extra = {}
        if industry_standard:
            extra["industryStandard"] = industry_standard
        if position_type:
            extra["positionType"] = position_type
        jobs.append({
            "url": FUND_INDUSTRY_ALLOCATION_URL,
            "module": "industry_allocation",
            "label": "持股行业分布",
            "field_cn": INDUSTRY_FIELD_CN,
            "extra": extra,
        })
    if "bond" in types:
        jobs.append({
            "url": FUND_BOND_TYPE_ALLOCATION_URL,
            "module": "bond_type_allocation",
            "label": "持有券种分布",
            "field_cn": BOND_FIELD_CN,
        })
    if "fund" in types:
        jobs.append({
            "url": FUND_FUND_TYPE_ALLOCATION_URL,
            "module": "fund_type_allocation",
            "label": "持有基金类型分布",
            "field_cn": FUND_FIELD_CN,
        })
    return query_by_codes(
        method_name=METHOD_NAME,
        securities=securities,
        jobs=jobs,
        output_dir=output_dir,
        start_date=start_date,
        end_date=end_date,
        extra_notes=notes,
    )


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="基金持仓分布：资产配置（默认）/ 持股行业 / 持有券种 / 持有基金类型",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--securities", required=True, help="基金代码/简称/拼音，逗号分隔；亦可传 .csv 路径")
    parser.add_argument(
        "--type",
        "-t",
        default="asset",
        help="asset(资产配置) / industry(持股行业) / bond(持有券种) / fund(持有基金类型)，逗号分隔；all 全部",
    )
    add_date_args(parser, daily_default=False)
    parser.add_argument("--asset-level", default=None, help="仅资产配置：level1 / level2，逗号分隔；不传返回全部层级")
    parser.add_argument(
        "--industry-standard",
        default=None,
        help="仅持股行业：swIndustry(申万一级，接口默认) / citicIndustry(中信一级)",
    )
    parser.add_argument(
        "--position-type",
        default=None,
        help="仅持股行业：top(重仓，接口默认) / all(全部持股，仅半年报与年报)",
    )
    add_output_arg(parser)
    args = parser.parse_args()

    try:
        securities = normalize_securities_arg(args.securities)
    except Exception as e:
        print(f"解析 --securities 失败: {e}")
        sys.exit(1)
    if not securities:
        parser.error("请指定 --securities")

    levels, err = parse_choices(args.asset_level, LEVEL_ALIAS, "资产层级")
    if err:
        parser.error(err)
    standard, err = parse_choice(args.industry_standard, STANDARD_ALIAS, "行业分类标准")
    if err:
        parser.error(err)
    position, err = parse_choice(args.position_type, POSITION_ALIAS, "持仓类型")
    if err:
        parser.error(err)

    print(
        fund_allocation(
            securities,
            query_type=args.type,
            start_date=args.start_date,
            end_date=args.end_date,
            asset_level=levels or None,
            industry_standard=standard,
            position_type=position,
            output_dir=args.output_dir or None,
        )
    )


if __name__ == "__main__":
    sys.stdout = TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="ignore")
    main()
